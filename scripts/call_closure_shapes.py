"""Fail-closed source-shape extraction for the call-closure report.

This is a bounded C++ source reader, not a second transport policy. Unsupported
expressions remain obligations. Only production Run APIs issue probe requests;
callee ABIs validate shapes and never supply missing caller operand counts.
"""
import hashlib
import json
import re
from bisect import bisect_right
from pathlib import Path


def split(text):
    result=[]; start=0; depth=0
    for i,c in enumerate(text):
        if c in '({[': depth+=1
        elif c in ')}]': depth-=1
        elif c==',' and depth==0:
            result.append(text[start:i].strip());start=i+1
    if text[start:].strip():result.append(text[start:].strip())
    return result


def close(text, start, left='(', right=')'):
    depth=1
    for i in range(start+1,len(text)):
        depth+=(text[i]==left)-(text[i]==right)
        if not depth:return i
    raise ValueError('unbalanced source')


def clean(text):
    return re.sub(r'//[^\n]*|/\*[\s\S]*?\*/',lambda m: ''.join('\n' if c=='\n' else ' ' for c in m[0]),text)


def substitute(text, bindings):
    return re.sub(r'(?<!\.)(?<!->)\b[A-Za-z_]\w*\b',lambda m: bindings.get(m[0],m[0]),text)


def integer(text):
    text=text.strip()
    while text.startswith('(') and close(text,0)==len(text)-1:text=text[1:-1].strip()
    # Conditional expressions with a statically known selector only.
    depth=0; question=None
    for i,c in enumerate(text):
        if c=='?' and depth==0:question=i;break
        depth+=(c=='(')-(c==')')
    if question is not None:
        nested=0; depth=0
        for j in range(question+1,len(text)):
            c=text[j];depth+=(c=='(')-(c==')')
            if depth==0:
                if c=='?':nested+=1
                elif c==':':
                    if nested:nested-=1
                    else:
                        test=integer(text[:question])
                        if test is None:return None
                        return integer(text[question+1:j] if test else text[j+1:])
    text=re.sub(r'\b(0x[0-9a-fA-F]+|\d+)[uUlL]*\b',r'\1',text)
    text=re.sub(r'\btrue\b','1',text);text=re.sub(r'\bfalse\b','0',text)
    text=text.replace('CLAW_CONTEXT_ALL','2047').replace('CLAW_SOURCE_PRESERVABLE','1138')
    text=text.replace('&&',' and ').replace('||',' or ')
    text=re.sub(r'!(?!=)',' not ',text)
    if re.search(r'[^0-9a-fx\s()+*/%<>=!&|~.\-notadr]',text):return None
    try:return int(eval(text,{'__builtins__':{}},{}))
    except Exception:return None


def alternatives(text, domains=None):
    """Finite literal destinations of a conditional, never an unknown value."""
    text=text.strip()
    while text.startswith('(') and close(text,0)==len(text)-1:text=text[1:-1].strip()
    value=integer(text)
    if value is not None:return {value}
    if domains and text in domains:return domains[text]
    depth=0
    for i,c in enumerate(text):
        if c=='?' and depth==0:
            nested=0;level=0
            for j in range(i+1,len(text)):
                d=text[j];level+=(d in '([{')-(d in ')]}')
                if level:continue
                if d=='?':nested+=1
                elif d==':':
                    if nested:nested-=1
                    else:
                        left,right=alternatives(text[i+1:j],domains),alternatives(text[j+1:],domains)
                        return left|right if left and right else set()
        depth+=(c in '([{')-(c in ')]}')
    return set()


class SourceShapes:
    def __init__(self, root, manifest, include_memory=False, import_slots=(), include_virtual=False):
        self.functions={};self.by_file={};self.ambiguous=set();self.files={};self.manifest=manifest
        self.root=root;self.borrowed={};self.constants={};self.include_memory=include_memory
        self.import_slots=set(import_slots)
        self.include_virtual=include_virtual
        paths=list(manifest['sources'])
        for shared in manifest.get('shared_sources',[]):
            if isinstance(shared,dict):paths+=shared.get('paths',shared.get('sources',[]))
        for path in paths:
            if not path.endswith(('.cpp','.hpp','.h')):continue
            raw=(root/path).read_text();text=clean(raw);self.files[path]=raw
            self.constants[path]={m[1]:m[2] for m in re.finditer(r'\b(?:constexpr|const)\s+uint32_t\s+(\w+)\s*=\s*([^;]+);',text) if integer(m[2]) is not None}
            for m in re.finditer(r'(?m)^\s*(?:(?:static|inline|explicit|\[\[noreturn\]\])\s+)*(?:[\w:<>]+[ &*]+)?(\w+)\s*\(',text):
                name=m[1]
                if name in ('if','while','switch','for','catch','return'):continue
                op=text.index('(',m.start());end=close(text,op);after=end+1
                while after<len(text) and text[after].isspace():after+=1
                if text[after:after+5]=='const':after+=5
                while after<len(text) and text[after].isspace():after+=1
                if after>=len(text) or text[after]!='{':continue
                stop=close(text,after,'{','}')
                params=[];defaults={}
                for p in split(text[op+1:end]):
                    p=p.split('=',1)[0].strip();names=re.findall(r'\b\w+\b',p)
                    pointer=re.search(r'\(\s*\*\s*(\w+)\s*\)',p)
                    params.append(pointer[1] if pointer else names[-1] if len(names)>1 else '')
                    original=split(text[op+1:end])[len(params)-1]
                    if '=' in original:defaults[params[-1]]=original.split('=',1)[1].strip()
                fn=dict(text=text[after+1:stop],params=params,defaults=defaults,path=path,offset=after+1)
                previous=self.by_file.get((path,name))
                if previous and previous['offset']!=fn['offset']:self.ambiguous.add((path,name))
                self.by_file[(path,name)]=fn
                # Owned translation units precede borrowed ones. In particular,
                # a borrowed module's dispatcher must not replace this entry.
                self.functions.setdefault(name,fn)
            # A local constant is visible only after its declaration in its
            # own function. Do not export it as a file-wide selector binding.
            self.constants[path]={m[1]:m[2] for m in re.finditer(r'\b(?:constexpr|const)\s+uint32_t\s+(\w+)\s*=\s*([^;]+);',text)
                if integer(m[2]) is not None and not any(p==path and f['offset']<=m.start()<f['offset']+len(f['text'])
                    for (p,_),f in self.by_file.items())}
        self.cache={}
        self.runtime='Sources/ClawRuntime.hpp'

    def resolve(self,name,path=None):
        name=name.rsplit('::',1)[-1]
        if path is None:
            fn=self.functions.get(name)
            return fn if fn and (fn['path'],name) not in self.ambiguous else None
        if (path,name) in self.ambiguous:return None
        if (path,name) in self.by_file:return self.by_file[(path,name)]
        candidates=[fn for (p,n),fn in self.by_file.items() if n==name]
        return candidates[0] if len(candidates)==1 and (candidates[0]['path'],name) not in self.ambiguous else None

    def target_reader(self,target):
        if any(int(o['address'],16)==target for o in self.manifest['owned']):return self
        for shared in self.manifest.get('shared_sources',[]):
            if not isinstance(shared,dict) or not shared.get('family'):continue
            family=shared['family']
            if family not in self.borrowed:
                manifest=json.loads((self.root/'Tests/families'/f'{family}.json').read_text())
                self.borrowed[family]=(SourceShapes(self.root,manifest,self.include_memory,self.import_slots)
                    if manifest.get('evidence',{}).get('level')=='admitted' and
                       manifest.get('program','claw-v1.0')==self.manifest.get('program','claw-v1.0') else None)
            reader=self.borrowed[family]
            if reader and any(int(o['address'],16)==target for o in reader.manifest['owned']):return reader
        return None

    def destinations(self, expression, domains=None):
        # An import dereference identifies a slot only when that slot exists
        # in the hash-checked original. Arbitrary loads stay indirect.
        match=re.fullmatch(r'run\.get\(([^()]*)\)',expression.strip())
        if match and integer(match[1]) in self.import_slots:return {integer(match[1])}
        return alternatives(expression,domains)

    def region(self, text, bindings):
        # Only prune a switch on the entry selector. Nested data-dependent
        # switches and branches are retained as potential paths.
        m=re.search(r'switch\s*\(\s*(\w+)\s*\)\s*\{',text)
        if not m or integer(bindings.get(m[1],m[1])) is None:return text
        value=integer(bindings[m[1]]);start=m.end()-1;end=close(text,start,'{','}')
        depth=0;labels=[]
        for label in re.finditer(r'case\s+(0x[0-9a-f]+|\d+)\s*:|default\s*:',text[start+1:end]):
            at=start+1+label.start()
            # Braced cases may contain switches; reject nested labels.
            prefix=text[start+1:at]
            if prefix.count('{')!=prefix.count('}'):continue
            labels.append((at,start+1+label.end(),integer(label[1]) if label[1] else None))
        for i,(at,after,key) in enumerate(labels):
            if key==value:
                stop=labels[i+1][0] if i+1<len(labels) else end
                # Shared consecutive case labels.
                while i+1<len(labels) and not text[after:stop].strip():
                    i+=1;after=labels[i][1];stop=labels[i+1][0] if i+1<len(labels) else end
                return text[:start+1]+'\n'*(text[start+1:after].count('\n'))+text[after:stop]+text[end:]
        # A default often delegates ordinary entries from a source dispatcher.
        defaults=[(i,r) for i,r in enumerate(labels) if r[2] is None]
        if defaults:
            i,(at,after,_)=defaults[-1];stop=end
            return text[:start+1]+'\n'*text[start+1:after].count('\n')+text[after:stop]+text[end:]
        return ''

    def fold(self,text,bindings):
        # Fold only brace-delimited, constant conditions. Keep line positions.
        for m in list(re.finditer(r'\bif\s*\(',text))[::-1]:
            op=text.index('(',m.start());end=close(text,op)
            expression=substitute(text[op+1:end],bindings)
            expression=re.sub(r'owned\(\s*(0x[0-9a-f]+|\d+)\s*\)',lambda x:str(next((o['argc'] for o in self.manifest['owned'] if int(o['address'],16)==int(x[1],0)),-1)),expression)
            value=integer(expression)
            after=end+1
            while after<len(text) and text[after].isspace():after+=1
            if value is None or after>=len(text) or text[after]!='{':continue
            stop=close(text,after,'{','}');tail=stop+1
            while tail<len(text) and text[tail].isspace():tail+=1
            blank=lambda t: ''.join('\n' if c=='\n' else ' ' for c in t)
            if text[tail:tail+4]=='else':
                other=tail+4
                while other<len(text) and text[other].isspace():other+=1
                if text[other]!='{':continue
                finish=close(text,other,'{','}')
                if value:text=text[:tail]+blank(text[tail:finish+1])+text[finish+1:]
                else:text=text[:m.start()]+blank(text[m.start():other])+text[other:]
            elif not value:text=text[:m.start()]+blank(text[m.start():stop+1])+text[stop+1:]
        return text

    def calls(self, name, bindings, chain=(), depth=0,path=None,visited=(),domains=None):
        fn=self.resolve(name,path)
        if fn is None:return []
        identity=(fn['path'],name)
        if depth>20 or identity in visited:return []
        visited=visited+(identity,)
        bindings={**self.constants.get(fn['path'],{}),**fn['defaults'],**bindings};text=self.region(fn['text'],bindings);text=self.fold(text,bindings);out=[]
        inherited_domains=dict(domains or {})
        assignments={}
        for m in re.finditer(r'(?<![\w.>])\b(\w+)\s*=(?!=)\s*([^;]+);',text):
            assignments.setdefault(m[1],[]).append(substitute(m[2],bindings))
        scopes=[(0,())];stack=[]
        for at,char in enumerate(text):
            if char=='{':stack.append(at);scopes.append((at+1,tuple(stack)))
            elif char=='}' and stack:stack.pop();scopes.append((at+1,tuple(stack)))
        scope_positions=[p for p,_ in scopes]
        def scope_at(at):return scopes[bisect_right(scope_positions,at)-1][1]
        declarations=[(m[1],m.start(),scope_at(m.start())) for m in re.finditer(
            r'\b(?:const\s+)?(?:uint32_t|int32_t|auto|bool)\s+(\w+)\s*(?=[=;])',text)]
        def declaration(symbol,at):
            scope=scope_at(at)
            visible=[(pos,owner) for name,pos,owner in declarations if name==symbol and pos<=at and scope[:len(owner)]==owner]
            return max(visible,key=lambda v:(len(v[1]),v[0])) if visible else None
        def finite_domains(prefix,at):
            domains=dict(inherited_domains);seen={}
            for match in re.finditer(r'(?<![\w.>])\b(\w+)\s*=(?!=)\s*([^;]+);',prefix):
                if declaration(match[1],match.start())!=declaration(match[1],at):continue
                seen.setdefault(match[1],[]).append(substitute(match[2],bindings))
            for symbol,expressions in seen.items():
                values=[self.destinations(expr,domains) for expr in expressions]
                if all(values):domains[symbol]=set().union(*values)
                else:domains.pop(symbol,None)
            for match in re.finditer(r'\b(\w+)\s*(?:\+\+|--|[+*/%|&^-]=)',prefix):domains.pop(match[1],None)
            return domains
        # Locally assigned scalar selectors/continuations can be resolved after
        # binding helper parameters. Other expressions remain symbolic.
        for m in re.finditer(r'\b(?:uint32_t|const uint32_t|auto)\s+(\w+)\s*=\s*([^;]+);',text):
            expression=substitute(m[2],bindings)
            mutated=re.search(r'\b'+re.escape(m[1])+r'\s*(?:\+\+|--|[+*/%|&^-]=)',text)
            if not mutated and len(assignments.get(m[1],[]))==1 and integer(expression) is not None:bindings={**bindings,m[1]:str(integer(expression))}
        for m in re.finditer(r'(?<!\w)(?:(\w+)\.)?(\w+)\s*\(',text):
            obj,callee=m.groups()
            obj=bindings.get(obj,obj)
            apis=('call','icall','context_call','source_call','source_tail','call_x87_exact','call_x87','fastcall','callback_call')
            if self.include_virtual:apis+=('vcall',)
            bound_callee=bindings.get(callee,callee)
            child=self.resolve(bound_callee,fn['path'])
            if obj=='run' and callee not in apis and not (self.include_memory and callee in ('get','put')):continue
            if obj!='run' and child is None and not re.fullmatch(r'function_[0-9a-f]+',bound_callee) and not (callee.startswith('claw_') and callee.endswith('_entry')):continue
            op=text.index('(',m.start());end=close(text,op)
            args=[substitute(a,bindings) for a in split(text[op+1:end])]
            prefix=substitute(text[:m.start()],bindings)
            domains=finite_domains(text[:m.start()],m.start())
            evidence=dict(path=fn['path'],line=self.files[fn['path']][:fn['offset']].count('\n')+1+text[:m.start()].count('\n'),
                          helper=name,chain=list(chain)+( [name]),api=callee,args=args,prefix=prefix)
            evidence['target_values']=sorted(self.destinations(args[0],domains)) if args else []
            if obj=='run' and callee in apis:
                out.append(evidence)
            elif self.include_memory and obj=='run' and callee in ('get','put'):
                out.append(dict(evidence,api='memory',operation=callee))
            elif callee.startswith('claw_') and callee.endswith('_entry') and args and integer(args[0]) is not None:
                out.append(dict(evidence,api='canonical-local',api_symbol=callee,target=integer(args[0])))
            elif re.fullmatch(r'function_[0-9a-f]+',callee) and callee!=name:
                out.append(dict(evidence,api='local',target=int(callee[9:],16)))
            if bound_callee!=callee and re.fullmatch(r'function_[0-9a-f]+',bound_callee):
                out.append(dict(evidence,api='local',target=int(bound_callee[9:],16)))
            if child is not None and (obj is None or obj!='run'):
                out.append(dict(evidence,api='enter',callee=bound_callee))
                bound={p:a for p,a in zip(child['params'],args) if p}
                if bound_callee in ('body','execute','ownedBody') and any(p in ('function','f') and integer(bound.get(p,'')) is None for p in child['params']):continue
                for leaf in self.calls(bound_callee,bound,chain+(name,),depth+1,child['path'],visited,domains):
                    leaf['parents']=[evidence]+leaf.get('parents',[]);out.append(leaf)
        return out

    def entry_calls(self, caller, source=False):
        key=(caller,source)
        if key in self.cache:return self.cache[key]
        # Start at the real exported dispatcher rather than search unrelated
        # bodies in the same family. Source macros select their source body.
        alltext='\n'.join(text for path,text in self.files.items() if path in self.manifest['sources'])
        macro=re.search(r'CLAW_OPTIONAL_SOURCE_MODULE_ENTRY\(([^)]+)\)',alltext)
        if macro:
            fields=split(macro[1]);entry=fields[5] if source else fields[4]
        else:
            macro=re.search(r'CLAW_(?:GUEST_)?SOURCE_MODULE_ENTRY\(([^)]+)\)',alltext)
            if not macro:macro=re.search(r'CLAW_MODULE_ENTRY\(([^)]+)\)',alltext)
            if not macro:return []
            entry=split(macro[1])[-1]
        fn=self.resolve(entry)
        if not fn:return []
        bindings={p:v for p,v in zip(fn['params'],['run',str(caller),'receiver','arguments']) if p}
        result=self.calls(entry,bindings)
        self.cache[key]=result
        return result

    def legacy_credits_calls(self, caller):
        """Operands in the selected legacy credits body, without site election.

        The native credits adapter must be bound separately. These are source
        candidates, not canonical Run calls: invoke can compose a typed local
        owner before forwarding to its dependency, and virt uses a legacy
        function-table adapter before reading the object's actual slot.
        """
        fn=self.resolve('body')
        if fn is None or fn['params']!=['r','f','p','a']:return []
        text=self.region(fn['text'],{'f':str(caller)})
        if not text:return []
        result=[]
        for match in re.finditer(r'\br\.(invoke|virt)\s*\(',text):
            start=text.index('(',match.start());end=close(text,start)
            args=split(text[start+1:end])
            if len(args)<2:continue
            arguments=args[2] if len(args)>2 else '{}'
            shape=None
            if len(args)<=3 and arguments.startswith('{') and arguments.endswith('}'):
                values=split(arguments[1:-1])
                shape=dict(argc=len(values),argument_expressions=values,
                    receiver_expression=args[0] if match[1]=='virt' else args[1])
            result.append(dict(path=fn['path'],
                line=self.files[fn['path']][:fn['offset']].count('\n')+1+text[:match.start()].count('\n'),
                api='legacy-'+match[1],args=args,shape=shape,
                source=text[match.start():end+1],
                source_sha256=hashlib.sha256(self.files[fn['path']].encode()).hexdigest(),
                site_correspondence_complete=False))
        return result

    def masks(self, leaf, context, owned):
        defaults=owned.get('source_context',{})
        result={key:defaults.get(key) for key in ('input_mask','output_mask','preserve_mask')}
        # Follow the context's initializer into a frame helper when present.
        prefix=leaf['prefix']
        creator=re.findall(r'\b'+re.escape(context)+r'\s*=\s*(\w+)\s*\(([^;]+)\);',prefix)
        if creator:
            name,actual=creator[-1]
            fn=self.resolve(name,leaf['path'])
            if fn is not None:
                bindings={**fn['defaults'],**{p:a for p,a in zip(fn['params'],split(actual)) if p}}
                prefix=substitute(fn['text'],bindings)+'\n'+prefix
        for field,key in [('inputMask','input_mask'),('outputMask','output_mask'),('preserveMask','preserve_mask')]:
            values=re.findall(r'\b'+re.escape(context)+r'\.'+field+r'\s*=\s*([^;]+);',prefix)
            if values:result[key]=integer(values[-1])
        return result

    def shape(self, leaf, owned):
        api=leaf['api'];args=leaf['args'];q={}
        if api=='local':return dict(local=True)
        if api=='canonical-local':
            if len(args)!=6 or integer(args[3]) is None:return None
            return dict(local=True,direct_entry=leaf['api_symbol'],argc=integer(args[3])) if 'api_symbol' in leaf else dict(local=True,argc=integer(args[3]))
        if api=='enter':return None
        if api=='icall':
            if not args:return None
            arguments=args[1] if len(args)>1 else '{}'
            if len(args)>2 or not arguments.startswith('{') or not arguments.endswith('}'):return None
            values=split(arguments[1:-1])
            return dict(argc=len(values),receiver=0,receiver_expression='0',argument_expressions=values)
        if len(args)<2:return None
        if api=='context_call':
            context=re.escape(args[1]);fields={}
            for field,key in [('inputMask','input_mask'),('outputMask','output_mask')]:
                values=re.findall(r'\b'+context+r'\.'+field+r'\s*=\s*([^;]+);',leaf['prefix'])
                if not values or integer(values[-1]) is None:return None
                fields[key]=integer(values[-1])
            values=re.findall(r'\b'+context+r'\.continuation\s*=\s*([^;]+);',leaf['prefix'])
            if not values or integer(values[-1]) is None:return None
            fields['compiler_return_pc']=integer(values[-1])
            ebp=re.findall(r'\b'+context+r'\.ebp\s*=\s*([^;]+);',leaf['prefix'])
            if not ebp:return None
            fields['compiler_ebp_expression']=ebp[-1]
            return dict(compiler=1,argc=0,receiver=0,**fields)
        if api in ('call','fastcall','call_x87'):
            pos=3 if api in ('fastcall','call_x87') else 2
        elif api=='source_call':pos=4
        elif api=='callback_call':pos=3
        elif api=='call_x87_exact':pos=3
        elif api=='source_tail':pos=None
        else:return None
        arguments=args[pos] if pos is not None and len(args)>pos else '{}'
        if not arguments.startswith('{') or not arguments.endswith('}'):return None
        q['argc']=len(split(arguments[1:-1]));q['receiver']=0 if integer(args[1])==0 else 0x61000000
        q['receiver_expression']=args[1];q['argument_expressions']=split(arguments[1:-1])
        if api=='callback_call':
            # Run::callback_cpu validates these exact masks before
            # callback_call copies that CPU into source_call. Activation and
            # the callback pointer remain explicit transport obligations.
            runtime=(self.root/self.runtime).read_text()
            signature='ClawSourceContext &callback_cpu() const'
            if signature not in runtime:return None
            start=runtime.index('{',runtime.index(signature));stop=close(runtime,start,'{','}')
            contract=runtime[start:stop]
            masks={field:re.search(r'c->cpu\.'+field+r' != (\w+)',contract) for field in ('inputMask','outputMask','preserveMask')}
            if not all(masks.values()):return None
            values=[integer(masks[f][1]) for f in ('inputMask','outputMask','preserveMask')]
            if any(v is None for v in values):return None
            pcs=alternatives(args[2]);pop=integer(args[4] if len(args)>4 else '0')
            if not pcs or pop is None:return None
            q.update(callback=1,source=1,input_mask=values[0],output_mask=values[1],preserve_mask=values[2],
                     return_pop=pop,return_pcs=sorted(pcs))
        if api=='fastcall':
            if len(args)<3:return None
            q['receiver2']=0 if integer(args[2])==0 else 0x62000000
            q['receiver2_expression']=args[2]
        if api in ('source_call','source_tail'):
            masks=self.masks(leaf,args[3],owned)
            if any(v is None for v in masks.values()):return None
            q.update(masks,source=1,tail=int(api=='source_tail'))
            if api=='source_call':
                pop=args[6] if len(args)>6 else '0'
                pop=re.sub(r'uint32_t\(\{[^}]*\}\.size\(\)\)',str(q['argc']),pop)
                q['return_pop']=integer(pop)
                if q['return_pop'] is None:return None
                q['return_pc']=integer(args[2])
                if q['return_pc'] is None:return None
            else:q['transfer_site']=integer(args[2])
        if api=='call_x87_exact':
            state=re.escape(args[2]);prefix=leaf['prefix']
            # Aggregate initialization zeroes every member before explicit
            # stores. This is a caller-side fact, not a target ABI default.
            prefix=re.sub(r'(\bClawX87State\s+'+state+r'\s*\{\}\s*;)',
                          lambda m:m[0]+f' {args[2]}.popCount = 0; {args[2]}.pushCount = 0;',prefix)
            # Run::x87_entry checks pop=push=0. Preserve that fact only at
            # the initializer's position, before any later explicit updates.
            prefix=re.sub(r'(\b'+state+r'\s*=\s*run\.x87_entry\([^;]+;)',
                          lambda m:m[0]+f' {args[2]}.popCount = 0; {args[2]}.pushCount = 0;',prefix)
            # Expand straight-line receipt setters; no arbitrary helper or
            # conditional effect is assumed to preserve the x87 request.
            for match in list(re.finditer(r'\b(\w+)\s*\(',prefix))[::-1]:
                name=match[1]
                fn=self.resolve(name,leaf['path'])
                if fn is None:continue
                op=prefix.index('(',match.start());end=close(prefix,op)
                actual=split(prefix[op+1:end])
                if args[2] not in actual:continue
                effect=substitute(fn['text'],dict(zip(fn['params'],actual)))
                if re.fullmatch(r'(?:\s*[\w.]+\s*=\s*[^;{}()]+;\s*)+',effect):
                    prefix=prefix[:match.start()]+effect+prefix[end+1:]
            for field,key in [('popCount','x87_pop'),('pushCount','x87_push')]:
                values=re.findall(state+r'\.'+field+r'\s*=\s*([^;]+);',prefix)
                if not values or integer(values[-1]) is None:return None
                q[key]=integer(values[-1])
            q['x87']=1
        elif api=='call_x87':
            if len(args)<3:return None
            q.update(x87_scalar=1,x87_expression=args[2])
        return q

    def edge(self, edge, owned, instruction_size):
        source=bool(owned.get('source_context') or owned.get('compiler_context'))
        leaves=self.entry_calls(edge['caller'],source)
        matches=[];unsupported=False
        for leaf in leaves:
            if leaf['api']=='memory':continue
            targets={leaf['target']} if leaf['api'] in ('local','canonical-local') else set(leaf.get('target_values',[]))
            if edge['target'] not in targets:continue
            if leaf['api']=='callback_call':
                if edge['site']+instruction_size not in alternatives(leaf['args'][2]):continue
            if leaf['api']=='source_call' and integer(leaf['args'][2]) is not None and integer(leaf['args'][2])!=edge['site']+instruction_size:continue
            if leaf['api']=='source_tail' and integer(leaf['args'][2]) is not None and integer(leaf['args'][2])!=edge['site']:continue
            q=self.shape(leaf,owned)
            if q and q.get('callback'):
                q['return_pc']=edge['site']+instruction_size
                q.pop('return_pcs')
            if q and q.get('compiler') and q['compiler_return_pc']!=edge['site']+instruction_size:continue
            if q is None:
                if leaf['api']!='enter':unsupported=True
                continue
            matches.append((leaf,q))
        if unsupported:return None
        if not matches:
            # Local dispatchers carry an explicit owned address selector. The
            # recursive body need not be expanded again to prove no host edge.
            for leaf in leaves:
                if leaf['api']!='enter':continue
                fn=self.resolve(leaf['callee'],leaf['path'])
                if fn is None:continue
                for param,actual in zip(fn['params'],leaf['args']):
                    if param in ('function','f') and edge['target'] in alternatives(actual) and leaf['callee'] in ('body','execute','ownedBody'):
                        matches.append((leaf,dict(local=True)))
            # Some admitted entries wrap a named implementation instead of an
            # address dispatcher. Derive that alias from the selected entry,
            # then require the caller to invoke the identical implementation.
            target_reader=self.target_reader(edge['target'])
            if target_reader:
                target_owned=next(o for o in target_reader.manifest['owned'] if int(o['address'],16)==edge['target'])
                targets=target_reader.entry_calls(edge['target'],bool(target_owned.get('source_context')))
                aliases=[]
                for t in targets:
                    if t['api']!='enter':continue
                    chain=t['chain']
                    def wrapper(name):
                        fn=target_reader.resolve(name,t['path'])
                        if fn is None:return False
                        text=re.sub(r'\(void\)\w+\s*;','',fn['text']).strip()
                        text=re.sub(r'\b(?:X87|ClawX87State)\s+\w+\s*(?:\{\})?\s*;','',text).strip()
                        # A thin ABI adapter calls one named core and may then
                        # return zero. Do not turn a core's callees into aliases.
                        return bool(re.fullmatch(r'(?:return\s+)?\w+\([^;]+\);\s*(?:return\s+0\s*;)?',text))
                    if len(chain)==1 or all(wrapper(n) for n in chain[1:]):
                        definition=target_reader.resolve(t['callee'],t['path'])
                        if definition:aliases.append((t['callee'],definition['path']))
                for leaf in leaves:
                    if leaf['api']!='enter' or leaf['callee'] in ('push','pop','invoke','child','internal','sourceCall'):continue
                    definition=self.resolve(leaf['callee'],leaf['path'])
                    if definition and (leaf['callee'],definition['path']) in aliases:
                        witness=dict(leaf,local_target=dict(family=target_reader.manifest['id'],
                            source=definition['path'],symbol=leaf['callee'],address=edge['target']))
                        matches.append((witness,dict(local=True)))
        if not matches:return None
        exact=[(l,q) for l,q in matches if l['api'] in ('source_call','source_tail')]
        if exact:matches=exact
        # Retain every legitimate variant; the compiled probe must accept all.
        shapes={str({k:v for k,v in q.items() if k not in ('receiver_expression','argument_expressions')}) for _,q in matches}
        if len(shapes)>1:
            variants=[]
            for leaf,q in matches:
                evidence={k:v for k,v in leaf.items() if k not in ('prefix','parents')}
                evidence['parents']=[{k:v for k,v in p.items() if k not in ('prefix','parents')} for p in leaf.get('parents',[])]
                variants.append(dict(shape=q,evidence=evidence))
            return dict(variants=[v['shape'] for v in variants]),dict(variants=variants)
        leaf,q=matches[0]
        evidence={k:v for k,v in leaf.items() if k not in ('prefix','parents')}
        evidence['parents']=[{k:v for k,v in p.items() if k not in ('prefix','parents')} for p in leaf.get('parents',[])]
        evidence['matched_source_paths']=[{k:v for k,v in l.items() if k not in ('prefix','parents')} for l,_ in matches]
        if q.get('source'):
            evidence['inherited_source_contract']=owned.get('source_context')
            evidence['context_assignments']=re.findall(r'\b\w+\.(?:inputMask|outputMask|preserveMask)\s*=\s*[^;]+;',leaf['prefix'])
        if q.get('x87'):
            evidence['x87_assignments']=re.findall(r'[\w.]+\.(?:popCount|pushCount)\s*=\s*[^;]+;',leaf['prefix'])
            evidence['depth_domain']='Every count accepted by Run::x87_transfer: popCount <= count <= 8 - pushCount + popCount.'

        return q,evidence


def self_test():
    """Shared dispatchers and same-named file-local helpers cannot alias."""
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory);(root/'Tests/families').mkdir(parents=True)
        (root/'main.cpp').write_text('''
uint32_t localHelper(Run &run, uint32_t receiver) { return run.call(0x300, receiver); }
uint32_t function_200_body(Run &run, uint32_t receiver) { X87 fp; return borrowed(run, receiver); }
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) { case 0x100: return function_200_body(run, receiver); }
}
CLAW_MODULE_ENTRY(main_entry, owned, body)
''')
        (root/'shared.cpp').write_text('''
uint32_t localHelper(Run &run, uint32_t receiver) { return run.call(0x300, receiver, {1, 2}); }
uint32_t borrowed(Run &run, uint32_t receiver) { return localHelper(run, receiver); }
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) { case 0x200: return borrowed(run, receiver); }
}
CLAW_MODULE_ENTRY(shared_entry, owned, body)
''')
        shared=dict(id='shared',sources=['shared.cpp'],owned=[dict(address='0x200')],evidence=dict(level='admitted'))
        path=root/'Tests/families/shared.json';path.write_text(json.dumps(shared))
        manifest=dict(id='main',sources=['main.cpp'],owned=[dict(address='0x100')],
                      shared_sources=[dict(family='shared',sources=['shared.cpp'])])
        edge=dict(caller=0x100,site=0x105,target=0x300,kind='call')
        reader=SourceShapes(root,manifest)
        assert reader.edge(edge,{},5)[0]['argc']==2
        proof=reader.edge(dict(edge,target=0x200),{},5)
        assert proof[0]==dict(local=True) and proof[1]['local_target']['source']=='shared.cpp'
        shared['program']='claw-v1.3';path.write_text(json.dumps(shared))
        assert SourceShapes(root,manifest).edge(dict(edge,target=0x200),{},5) is None
        (root/'main.cpp').write_text((root/'main.cpp').read_text()+
            '\nuint32_t function_200_body(Run &run) { return 0; }\n')
        assert SourceShapes(root,manifest).resolve('function_200_body','main.cpp') is None
        (root/'main.cpp').write_text('''// Keep source offsets despite long comments.
uint32_t relay(Run &run, uint32_t function, uint32_t receiver) {
    return run.call(function, receiver, {7});
}
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) {
    case 0x100: {
        run.call(0x300, receiver, {1});
        run.call(0x300, 0, {1, 2});
        run.icall(0x546d58, {receiver, receiver + 0x128});
        run.icall(0x546d5c, {receiver, 1, 2, 3, 4});
        relay(run, receiver ? 0x301 : 0x302, receiver);
        uint32_t unknown = 0x303;
        unknown = run.get(receiver);
        run.call(unknown, receiver);
        uint32_t later;
        run.call(later, receiver);
        later = 0x304;
        uint32_t changed = 0x305;
        changed++;
        run.call(changed, receiver);
        if (receiver) {
            uint32_t decoder = 0x306;
            run.call(decoder, receiver, {1});
        } else {
            uint32_t decoder = 0x307;
            run.call(decoder, receiver, {1, 2});
        }
        return 0;
    }
    }
}
CLAW_MODULE_ENTRY(main_entry, owned, body)
''')
        manifest['shared_sources']=[]
        reader=SourceShapes(root,manifest)
        variants=reader.edge(edge,{},5)[0]['variants']
        assert {(v['argc'],v['receiver']) for v in variants}=={(1,0x61000000),(2,0)}
        for target in (0x301,0x302):
            assert reader.edge(dict(edge,target=target),{},5)[0]['argc']==1
        for target in (0x303,0x304,0x305):assert reader.edge(dict(edge,target=target),{},5) is None
        assert reader.edge(dict(edge,target=0x306),{},5)[0]['argc']==1
        assert reader.edge(dict(edge,target=0x307),{},5)[0]['argc']==2
        for target,count in ((0x546d58,2),(0x546d5c,5)):
            imported=reader.edge(dict(edge,target=target),{},6)[0]
            assert imported['argc']==count and imported['receiver']==0
        leaf=next(l for l in reader.entry_calls(0x100) if l['api']=='call' and l['args'][0]=='0x300')
        assert (root/'main.cpp').read_text().splitlines()[leaf['line']-1].strip()=='run.call(0x300, receiver, {1});'
        assert substitute('context.ebp = ebp;',{'ebp':'0'})=='context.ebp = 0;'
        assert reader.shape(dict(api='fastcall',args=['0x300','receiver','edx','{1}']),{})['receiver2']==0x62000000
        assert reader.shape(dict(api='fastcall',args=['0x300','receiver','0','{1}']),{})['receiver2']==0
        scalar=reader.shape(dict(api='call_x87',args=['0x300','0','value','{1, 2}']),{})
        assert scalar['x87_scalar']==1 and scalar['argc']==2 and scalar['x87_expression']=='value'
        assert reader.shape(dict(api='icall',args=['0x546d58','{rect, actor + 0x128}']),{})==dict(
            argc=2,receiver=0,receiver_expression='0',argument_expressions=['rect','actor + 0x128'])
        assert reader.shape(dict(api='icall',args=['0x546d58']),{})['argc']==0
        assert reader.shape(dict(api='icall',args=['0x546d58','unknown']),{}) is None
        (root/'main.cpp').write_text('''
const uint32_t importSlot = 0x546d50;
uint32_t api(Run &r, uint32_t slot, std::initializer_list<uint32_t> args = {}) {
    return r.call(slot, 0, args);
}
uint32_t fromSlot(Run &run, uint32_t slot, std::initializer_list<uint32_t> args) {
    uint32_t destination = run.get(slot);
    return run.call(destination, 0, args);
}
uint32_t body(Run &r, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) { case 0x100: {
        api(r, importSlot, {receiver, 7});
        r.call(r.get(importSlot), 0, {1, 2, 3, 4});
        fromSlot(r, importSlot, {5});
        r.call(r.get(0x600000), receiver, {1});
        return 0;
    } }
}
CLAW_MODULE_ENTRY(main_entry, owned, body)
''')
        imported_edge=dict(edge,target=0x546d50,immediate=False)
        reader=SourceShapes(root,manifest,import_slots={0x546d50})
        shapes=reader.edge(imported_edge,{},6)[0]['variants']
        assert {q['argc'] for q in shapes}=={1,2,4}
        assert all(q['receiver']==0 for q in shapes)
        assert reader.edge(dict(edge,target=0x600000),{},6) is None
        untrusted=SourceShapes(root,manifest)
        # The literal API still names its destination, but memory dereferences
        # cannot be identified as imports without original IAT evidence.
        assert untrusted.edge(imported_edge,{},6)[0]['argc']==2
        assert reader.destinations('run.get(receiver)')==set()
        (root/'Sources').mkdir()
        (root/'Sources/ClawRuntime.hpp').write_text('''
ClawSourceContext &callback_cpu() const {
    if (c->cpu.inputMask != CLAW_CONTEXT_ALL || c->cpu.outputMask != CLAW_CONTEXT_ALL ||
        c->cpu.preserveMask != CLAW_SOURCE_PRESERVABLE) fail();
    return c->cpu;
}
''')
        (root/'main.cpp').write_text('''
uint32_t body(Run &run, uint32_t function, uint32_t receiver, const uint32_t *arguments) {
    switch (function) { case 0x100: {
        run.callback_call(run.get(0x546d50), receiver, receiver ? 0x10b : 0x11b, {7}, 4);
        run.icall(0x546d50, {8});
        return 0;
    } }
}
CLAW_MODULE_ENTRY(main_entry, owned, body)
''')
        reader=SourceShapes(root,manifest,import_slots={0x546d50})
        for site in (0x105,0x115):
            variants=reader.edge(dict(imported_edge,site=site),{},6)[0]['variants']
            callback=next(q for q in variants if q.get('callback'))
            assert callback['source']==1 and callback['receiver']==0x61000000
            assert callback['return_pc']==site+6 and callback['return_pop']==4
            assert (callback['input_mask'],callback['output_mask'],callback['preserve_mask'])==(2047,2047,1138)
        assert not reader.edge(dict(imported_edge,site=0x125),{},6)[0].get('callback')
    print(json.dumps(dict(check='call-closure-shape-reader',status='pass')))


if __name__=='__main__':
    self_test()
