import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const target = path.join(root, 'research/node_modules/rea-agents/dist/domain/dosMz.js');
let source = fs.readFileSync(target, 'utf8');
const marker = '    const headerBytes = bytes.readUInt16LE(8) * 16;';
const patch = `    // Local compatibility fix: prefer a bounded explicit PE signature.
    const declaredPE = bytes.readUInt32LE(60);
    if (declaredPE >= 64 && declaredPE <= bytes.length - 24 &&
        bytes.toString("binary", declaredPE, declaredPE + 4) === "PE\\u0000\\u0000")
        return declaredPE;
`;
if (!source.includes('const declaredPE =')) {
    if (!source.includes(marker)) throw new Error('REA source changed; inspect the detection patch');
    source = source.replace(marker, patch + marker);
    fs.writeFileSync(target, source);
}
const { mzWindowsHeaderOffset } = await import(target);
const bytes = Buffer.alloc(128);
bytes.write('MZ'); bytes.writeUInt16LE(2, 8); bytes.writeUInt32LE(64, 60); bytes.write('PE\0\0', 64, 'binary');
if (mzWindowsHeaderOffset(bytes) !== 64) throw new Error('Short-DOS-header PE regression');
bytes.writeUInt32LE(0xffffffff, 60);
if (mzWindowsHeaderOffset(bytes) !== null) throw new Error('Out-of-bounds PE regression');
console.log('PASS: REA bounded PE detection');
