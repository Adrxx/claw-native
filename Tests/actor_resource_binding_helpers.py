"""Private adapter extension; original registry lookup and generic binders execute."""
from logic_registry_helpers import RegistryHarness, packed
from unicorn.x86_const import UC_X86_REG_ECX,UC_X86_REG_ESP

class ActorBindingHarness(RegistryHarness):
    actor,secondary,actor_scene,image_resource,image_table,image_manager,image_buckets,image_nodes,associated,associated_vtable,metadata=range(0x1100000,0x110b000,0x1000)
    destructor=0x11ef000
    def __init__(self,exe):
        super().__init__(exe);self.populate();self.u.mem_map(0x1100000,0x100000)
        m=self.machine
        m.write_words(self.actor_scene+16,[self.image_manager,self.registry])
        m.write_words(self.image_manager+16+4,[self.image_buckets,17,0,self.image_nodes,0,32])
        for i in range(32):m.write_words(self.image_nodes+i*16,[self.image_nodes+(i+1)*16 if i<31 else 0,0,0,0])
        self.u.mem_write(self.image_buckets,bytes(17*4))
        self.u.mem_write(self.query,b'Images\0')
        slot=m.call(0x4f62a8,self.image_manager+16,packed(self.query));m.write_words(slot,[self.image_resource])
        self.u.mem_write(self.query,b'Handler\0')
        slot=m.call(0x4f62a8,self.registry+16,packed(self.query));m.write_words(slot,[self.metadata])
        m.write_words(self.associated,[self.associated_vtable]);m.write_words(self.associated_vtable,[self.destructor])
        self.events=[];self.capture=False;self.ready=True;self.allocation=True
    @staticmethod
    def mutate(actor,secondary,address):
        if address==0x4f63ec:actor[1]^=0x20;actor[2]^=0x40
        elif address==0x4f6428:actor[0xdc//4]=99;secondary[0x20//4]=0x1234
        elif address==ActorBindingHarness.destructor:actor[2]^=0x80;secondary[0x24//4]=0x5678
    def host(self,u,address,size,user):
        if not getattr(self,'ready',False):return super().host(u,address,size,user)
        m=self.machine;sp=u.reg_read(UC_X86_REG_ESP);receiver=u.reg_read(UC_X86_REG_ECX)
        if address==0x4f6286:
            if self.capture:
                name=m.read_words(sp+4,1)[0];self.events.append((address,receiver,0,self.text(name)))
            return # Execute full original map hash / strcmp / lookup.
        if address not in (0x4f63ec,0x4f6428,self.destructor):return super().host(u,address,size,user)
        if address==0x4f63ec:
            argument=m.read_words(sp+4,1)[0];assert argument==0x174
            event=(address,0,argument,None);pop=0;result=self.secondary if self.allocation else 0
        elif address==0x4f6428:
            argument=m.read_words(sp+4,1)[0];event=(address,0,argument,None);pop=0;result=0
        else:
            argument=m.read_words(sp+4,1)[0];assert argument==1 and receiver==self.associated
            event=(address,receiver,argument,None);pop=4;result=0
        if self.capture:self.events.append(event)
        aw=m.read_words(self.actor,128);sw=m.read_words(self.secondary,93);self.mutate(aw,sw,address);m.write_words(self.actor,aw);m.write_words(self.secondary,sw)
        self.returned(pop,result)
    def lookup(self,map_token,name):
        self.u.mem_write(self.query,name+b'\0');self.machine.write_words(self.output,[0])
        capture=self.capture;self.capture=False
        self.machine.call(0x4f6286,map_token,packed(self.query,self.output))
        self.capture=capture;return self.machine.read_words(self.output,1)[0]
