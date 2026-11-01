#!/usr/bin/env python3
"""Offline prototype: patch 6 SETFIELD sites of Violet 4.0.0 CE6.Get.

Proof: exact original SHA, bytecode opcode guards, source varint/lineinfo
integrity checks. No game runtime or emulator success implied.
"""
from __future__ import annotations
import argparse, hashlib, json, struct
from pathlib import Path
class R:
    def __init__(self, b):
        self.b=b; self.i=0; self.node_count=0
    def get(self,n):
        if n<0 or n>len(self.b)-self.i:raise ValueError(f"invalid read n={n} at offset {self.i:x}")
        out=self.b[self.i:self.i+n]; self.i+=n; return out
    def u8(self):return self.get(1)[0]
    def var(self):
        v=0
        for _ in range(10):
            b=self.u8(); v=(v<<7)|(b&127)
            if b&128:return v
        raise ValueError("overlong Lua 5.4 varuint")
    def s(self):
        n=self.var()
        return self.get(n-1).decode("utf8","replace") if n else None
SOURCE_SHA='c1a4f4e2625912cf0b739a642a79ba3357df0557a544b92da22a6cb139de2815'
ORIGINAL_SIZE=12912264
OFFSET_SJ=((1<<25)-1)//2
OP_JMP=56;OP_LOADI=1
FIELDS={153:('hpCoef',100,0x09240412),157:('powerChargeTrigerHp',0,0x09250412),161:('powerChargeTrigerTime',0,0x09260412),181:('powerChargeDamageRate',100,0x092B0412),185:('powerChargeGemDamageRate',100,0x092C0412),189:('powerChargeChargeGemDamageRate',100,0x092D0412)}
# Word bytes verified directly against original main.blua, independent of iABC assembler.
def encvar(n):
    assert isinstance(n,int) and n>=0
    pieces=[n&127];n>>=7
    while n: pieces.append(n&127);n>>=7
    pieces.reverse();pieces[-1]|=128
    return bytes(pieces)
def loadi(reg,value):
    assert -65535<=value<=65536
    return OP_LOADI|(reg<<7)|((value+65535)<<15)
def jmp(src,target):
    delta=target-(src+1)
    assert -OFFSET_SJ<=delta<=OFFSET_SJ
    return OP_JMP | ((delta+OFFSET_SJ)<<7)
class Audit(R):
    def __init__(self,raw):super().__init__(raw);self.matches=[]
    def node(self,p='root',depth=0):
        self.node_count+=1
        self.s();self.var();self.var();self.u8();self.u8();self.u8()
        code_count_pos=self.i;code_count=self.var();code_count_end=self.i
        code_start=self.i;codes=list(struct.unpack('<'+str(code_count)+'I',self.get(4*code_count)));code_end=self.i
        consts=[]
        for _ in range(self.var()):
            tag=self.u8()
            if tag==0:val=None
            elif tag in (1,17):val=bool(tag==17)
            elif tag==3:val=struct.unpack('<q',self.get(8))[0]
            elif tag==19:val=struct.unpack('<d',self.get(8))[0]
            elif tag in (4,20):val=self.s()
            else:raise ValueError('bad constant type')
            consts.append(val)
        self.get(self.var()*3)
        n=self.var()
        for j in range(n):self.node(p+'/'+str(j),depth+1)
        lines_pos=self.i;lines_count=self.var();lines_count_end=self.i
        lines_start=self.i;self.get(lines_count);lines_end=self.i
        for _ in range(self.var()):self.var();self.var()
        for _ in range(self.var()):self.s();self.var();self.var()
        for _ in range(self.var()):self.s()
        if p=='root/7833':self.matches.append(locals().copy())

def compile_patch(source,parameters):
    if len(source)!=ORIGINAL_SIZE or hashlib.sha256(source).hexdigest()!=SOURCE_SHA:raise ValueError('original Violet 4.0.0 main.blua SHA mismatch')
    rd=Audit(source); rd.get(31);rd.u8();rd.node();assert rd.i==len(source)
    assert len(rd.matches)==1
    info=rd.matches[0];n=info['code_count'];codes=info['codes'][:];consts=info['consts']
    assert n==538 and info['code_start']==0x52C407, 'unexpected CE6.Get layout'
    assert info['lines_count'] in (0,n),'unexpected Lua debug lineinfo shape'
    assert len(consts)==80
    settings={
        'hpCoef':parameters['hp_coef'],
        'powerChargeTrigerHp':0 if parameters['no_shield'] else None,
        'powerChargeTrigerTime':0 if parameters['no_shield'] else None,
        'powerChargeDamageRate':parameters['shield_rates'][0],
        'powerChargeGemDamageRate':parameters['shield_rates'][1],
        'powerChargeChargeGemDamageRate':parameters['shield_rates'][2],
    }
    # Haxe distinguishes external "powerChargeChangeGemDamageRate" resource key
    # from internal Haxe field "powerChargeChargeGemDamageRate" (typo in retail).
    scripts=[]
    for site,(key,default,original) in FIELDS.items():
        real=parameters['hp_coef'] if site==153 else settings[key]
        assert codes[site]==original, f'PC{site} opcode guard mismatch'
        assert consts[(original>>16)&255]==key, f'PC{site} field string mismatch'
        if real is None:continue
        assert 0<=real<=65535
        target=n+len(scripts)
        # Original SETFIELD replaced by unconditional branch to late stub:
        # LOADI R9, literal; ORIGINAL SETFIELD R8,k,R9; JMP back to site+1.
        codes[site]=jmp(site,target)
        scripts.extend([loadi(9,real),original,jmp(target+2,site+1)])
    assert scripts
    expanded=codes+scripts
    changed_original=[i for i in range(n) if codes[i]!=info['codes'][i]]
    assert changed_original==[site for site,(key,_,orig) in FIELDS.items() if settings[key] is not None]
    # Validate jump destinations and values to ensure stubs don't clobber live registers.
    for index,site in enumerate(changed_original):
        stub_start=n+3*index
        assert (expanded[site]>>7)-OFFSET_SJ +site+1==stub_start
        assert (expanded[stub_start+2]>>7)-OFFSET_SJ +stub_start+3==site+1
        assert expanded[stub_start+1]==info['codes'][site]
    new_code=struct.pack('<'+str(len(expanded))+'I',*expanded)
    edits=[(info['code_count_pos'],info['code_count_end'],encvar(len(expanded))),(info['code_start'],info['code_end'],new_code)]
    if info['lines_count']:
        edits.extend([(info['lines_pos'],info['lines_count_end'],encvar(info['lines_count']+len(scripts))),(info['lines_end'],info['lines_end'],bytes(len(scripts)))])
    out=bytearray(source)
    for start,end,rep in sorted(edits,reverse=True):out[start:end]=rep
    return bytes(out),{'main_original_sha256':SOURCE_SHA,'main_patched_sha256':hashlib.sha256(out).hexdigest(),'target':'CE6.Get root/7833','original_code_words':n,'patched_code_words':len(expanded),'changed_pc':changed_original,'stubs':len(scripts),'settings':parameters,'load_only_test':'PENDING','emulator_tested':False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original',type=Path,required=True,help='user-extracted unmodified Violet 4.0.0 main.blua')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--hp-coef',type=int,default=100)
    p.add_argument('--no-shield',action='store_true')
    p.add_argument('--shield-rates',type=int,nargs=3,default=None)
    p.add_argument('--report',type=Path)
    a=p.parse_args()
    if not 1<=a.hp_coef<=65535: p.error('hp coef requires 1..65535 experimental range')
    if a.shield_rates is not None and any(not 0<=x<=65535 for x in a.shield_rates):p.error('rates require 0..65535')
    config={'hp_coef':a.hp_coef,'no_shield':a.no_shield,'shield_rates':a.shield_rates if a.shield_rates is not None else [None,None,None]}
    out,report=compile_patch(a.original.read_bytes(),config)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_bytes(out)
    if a.report:a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()