import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressRange;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.RefType;
import ghidra.program.model.symbol.SourceType;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.TreeSet;

/**
 * One-run function corpus dump for the original v1.0 executable.
 *
 * Arguments:
 *   seed  SEEDS_FILE PHASE_A_JSON_OUT          Phase A. Mutates the program (run once, save).
 *   dump  CORPUS_DIR SHARD_INDEX SHARD_COUNT   Phase B. Read-only, resumable, shardable.
 *
 * Phase B writes CORPUS_DIR/c/<entry>.c and CORPUS_DIR/meta/<entry>.json per function.
 * Entries are 8 lowercase hex digits. Body ranges are [start, end_exclusive] integers.
 * Operates only on the analysis database, never on the input executable bytes.
 */
public class DumpProgram extends GhidraScript {
    private static final String ORIGINAL_SHA256 =
        "350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263";
    private static final int DECOMPILE_SECONDS = 60;
    private static final int MAX_STRINGS = 8;
    private static final int MAX_STRING_LENGTH = 60;

    private DecompInterface decompiler;

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        checkProgramIdentity();
        if (args.length == 3 && args[0].equals("seed")) {
            runPhaseA(args[1], args[2]);
        } else if (args.length == 4 && args[0].equals("dump")) {
            runPhaseB(args[1], Integer.parseInt(args[2]), Integer.parseInt(args[3]));
        } else {
            throw new IllegalArgumentException("seed SEEDS OUT | dump CORPUS_DIR INDEX COUNT");
        }
    }

    private void checkProgramIdentity() {
        String actual = currentProgram.getExecutableSHA256();
        if (!ORIGINAL_SHA256.equalsIgnoreCase(actual)) {
            throw new IllegalStateException("Corpus dump requires fingerprinted original v1.0");
        }
    }

    // ---------------------------------------------------------------- Phase A

    private void runPhaseA(String seedsFile, String outputFile) throws Exception {
        List<String> seedLines = Files.readAllLines(Path.of(seedsFile));
        List<String> interior = new ArrayList<>();
        List<String> created = new ArrayList<>();
        List<String> failed = new ArrayList<>();
        for (String line : seedLines) {
            String text = line.trim();
            if (text.isEmpty()) {
                continue;
            }
            Address entry = toAddr(text);
            String outcome = seedOne(entry);
            if (outcome.equals("interior")) {
                interior.add(hex8(entry));
            } else if (outcome.equals("created")) {
                created.add(hex8(entry));
            } else if (outcome.equals("failed")) {
                failed.add(hex8(entry));
            }
        }
        List<String> pointerSeeded = new ArrayList<>();
        scanPointers(pointerSeeded);
        StringBuilder json = new StringBuilder();
        json.append("{\"interior_seeds\":").append(stringList(interior));
        json.append(",\"seed_created\":").append(stringList(created));
        json.append(",\"seed_failed\":").append(stringList(failed));
        json.append(",\"pointer_seeded\":").append(stringList(pointerSeeded)).append("}");
        Files.writeString(Path.of(outputFile), json.toString(), StandardCharsets.UTF_8);
        println("Phase A: interior=" + interior.size() + " created=" + created.size()
            + " failed=" + failed.size() + " pointer_seeded=" + pointerSeeded.size());
    }

    /** Returns "existing", "interior", "created" or "failed". */
    private String seedOne(Address entry) {
        if (getFunctionAt(entry) != null) {
            return "existing";
        }
        if (getFunctionContaining(entry) != null) {
            return "interior";
        }
        disassemble(entry);
        Function function = createFunction(entry, null);
        return function == null ? "failed" : "created";
    }

    private void scanPointers(List<String> pointerSeeded) throws Exception {
        MemoryBlock text = currentProgram.getMemory().getBlock(".text");
        Address textStart = text.getStart();
        Address textEnd = text.getEnd();
        byte[] word = new byte[4];
        for (String blockName : new String[] {".rdata", ".data"}) {
            MemoryBlock block = currentProgram.getMemory().getBlock(blockName);
            if (block == null || !block.isInitialized()) {
                continue;
            }
            Address cursor = block.getStart();
            Address last = block.getEnd().subtract(3);
            while (cursor.compareTo(last) <= 0) {
                currentProgram.getMemory().getBytes(cursor, word);
                long value = (word[0] & 0xffL) | ((word[1] & 0xffL) << 8)
                    | ((word[2] & 0xffL) << 16) | ((word[3] & 0xffL) << 24);
                cursor = cursor.add(4);
                if (value < textStart.getOffset() || value > textEnd.getOffset()) {
                    continue;
                }
                Address target = toAddr(value);
                if (trySeedPointer(target)) {
                    pointerSeeded.add(hex8(target));
                }
            }
        }
    }

    private boolean trySeedPointer(Address target) {
        if (getFunctionContaining(target) != null) {
            return false;
        }
        Instruction existing = getInstructionContaining(target);
        if (existing != null && !existing.getAddress().equals(target)) {
            return false;
        }
        disassemble(target);
        if (getInstructionAt(target) == null) {
            return false;
        }
        Function function = createFunction(target, null);
        if (function == null) {
            return false;
        }
        if (bodyHasErrorBookmark(function)) {
            removeFunction(function);
            return false;
        }
        return true;
    }

    private boolean bodyHasErrorBookmark(Function function) {
        for (AddressRange range : function.getBody().getAddressRanges()) {
            Address cursor = range.getMinAddress();
            while (cursor != null && cursor.compareTo(range.getMaxAddress()) <= 0) {
                if (currentProgram.getBookmarkManager().getBookmark(cursor, "Error", "Bad Instruction") != null) {
                    return true;
                }
                cursor = cursor.next();
            }
        }
        return false;
    }

    // ---------------------------------------------------------------- Phase B

    private void runPhaseB(String corpusDir, int shardIndex, int shardCount) throws Exception {
        Path cDir = Path.of(corpusDir, "c");
        Path metaDir = Path.of(corpusDir, "meta");
        Files.createDirectories(cDir);
        Files.createDirectories(metaDir);
        List<Function> functions = new ArrayList<>();
        FunctionIterator iterator = currentProgram.getFunctionManager().getFunctions(true);
        while (iterator.hasNext()) {
            functions.add(iterator.next());
        }
        openDecompiler();
        try {
            int done = 0;
            for (int index = 0; index < functions.size(); index++) {
                if (index % shardCount != shardIndex) {
                    continue;
                }
                if (monitor.isCancelled()) {
                    break;
                }
                Function function = functions.get(index);
                String name = hex8(function.getEntryPoint());
                Path cFile = cDir.resolve(name + ".c");
                Path metaFile = metaDir.resolve(name + ".json");
                if (Files.exists(cFile) && Files.exists(metaFile)) {
                    continue;
                }
                dumpOne(function, cFile, metaFile);
                done++;
                if (done % 50 == 0) {
                    println("shard " + shardIndex + ": " + done + " functions dumped");
                }
            }
            println("shard " + shardIndex + " finished, " + done + " new functions");
        } finally {
            decompiler.dispose();
        }
    }

    private void openDecompiler() {
        decompiler = new DecompInterface();
        if (!decompiler.openProgram(currentProgram)) {
            throw new IllegalStateException(decompiler.getLastMessage());
        }
    }

    private void dumpOne(Function function, Path cFile, Path metaFile) throws Exception {
        String entry = hex8(function.getEntryPoint());
        String header = "// Original v1.0 entry: " + function.getEntryPoint() + "\n";
        String body;
        boolean ok = false;
        try {
            DecompileResults result = decompiler.decompileFunction(function, DECOMPILE_SECONDS, monitor);
            if (result.decompileCompleted()) {
                body = result.getDecompiledFunction().getC();
                ok = true;
            } else {
                body = "// DECOMPILE FAILED: " + oneLine(result.getErrorMessage()) + "\n";
            }
        } catch (Exception problem) {
            body = "// DECOMPILE FAILED: " + oneLine(String.valueOf(problem.getMessage())) + "\n";
            decompiler.dispose();
            openDecompiler();
        }
        String text = header + body;
        Files.writeString(cFile, text, StandardCharsets.UTF_8);
        Files.writeString(metaFile, metaJson(function, entry, text, ok), StandardCharsets.UTF_8);
    }

    private String metaJson(Function function, String entry, String cText, boolean ok) {
        StringBuilder json = new StringBuilder();
        json.append("{\"entry\":").append(quote(entry));
        json.append(",\"name\":").append(quote(function.getName()));
        json.append(",\"size\":").append(function.getBody().getNumAddresses());
        json.append(",\"ranges\":").append(rangesJson(function));
        json.append(",\"calling_convention\":").append(quote(String.valueOf(function.getCallingConventionName())));
        json.append(",\"is_thunk\":").append(function.isThunk());
        json.append(",\"callers\":").append(stringList(callers(function)));
        json.append(",\"callees\":").append(stringList(callees(function)));
        json.append(",\"decompile_ok\":").append(ok);
        json.append(",\"unaff_count\":").append(countOccurrences(cText, "unaff_"));
        json.append(",\"jumptable_warning\":").append(cText.toLowerCase().contains("jumptable"));
        json.append(",\"strings\":").append(stringList(strings(function))).append("}");
        return json.toString();
    }

    private String rangesJson(Function function) {
        StringBuilder json = new StringBuilder("[");
        boolean first = true;
        for (AddressRange range : function.getBody().getAddressRanges()) {
            if (!first) {
                json.append(",");
            }
            first = false;
            json.append("[").append(range.getMinAddress().getOffset());
            json.append(",").append(range.getMaxAddress().getOffset() + 1).append("]");
        }
        return json.append("]").toString();
    }

    private static boolean isCallOrJump(RefType type) {
        return type.isCall() || type.isJump();
    }

    private List<String> callers(Function function) {
        TreeSet<String> result = new TreeSet<>();
        ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(function.getEntryPoint());
        while (references.hasNext()) {
            Reference reference = references.next();
            if (!isCallOrJump(reference.getReferenceType())) {
                continue;
            }
            Function caller = getFunctionContaining(reference.getFromAddress());
            if (caller != null && !caller.getEntryPoint().equals(function.getEntryPoint())) {
                result.add(hex8(caller.getEntryPoint()));
            }
        }
        return new ArrayList<>(result);
    }

    private List<String> callees(Function function) {
        TreeSet<String> result = new TreeSet<>();
        InstructionIterator instructions = currentProgram.getListing().getInstructions(function.getBody(), true);
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            for (Reference reference : instruction.getReferencesFrom()) {
                if (!isCallOrJump(reference.getReferenceType()) || !reference.getToAddress().isMemoryAddress()) {
                    continue;
                }
                Function callee = getFunctionAt(reference.getToAddress());
                if (callee != null && !callee.getEntryPoint().equals(function.getEntryPoint())) {
                    result.add(hex8(callee.getEntryPoint()));
                }
            }
        }
        return new ArrayList<>(result);
    }

    private List<String> strings(Function function) {
        List<String> result = new ArrayList<>();
        InstructionIterator instructions = currentProgram.getListing().getInstructions(function.getBody(), true);
        while (instructions.hasNext() && result.size() < MAX_STRINGS) {
            Instruction instruction = instructions.next();
            for (Reference reference : instruction.getReferencesFrom()) {
                if (result.size() >= MAX_STRINGS || !reference.getToAddress().isMemoryAddress()) {
                    continue;
                }
                Data data = getDataAt(reference.getToAddress());
                if (data == null || !data.hasStringValue()) {
                    continue;
                }
                String value = String.valueOf(data.getValue());
                if (value.length() > MAX_STRING_LENGTH) {
                    value = value.substring(0, MAX_STRING_LENGTH);
                }
                if (!result.contains(value)) {
                    result.add(value);
                }
            }
        }
        return result;
    }

    // ---------------------------------------------------------------- helpers

    private static String hex8(Address address) {
        return String.format("%08x", address.getOffset());
    }

    private static int countOccurrences(String text, String needle) {
        int count = 0;
        int from = 0;
        while ((from = text.indexOf(needle, from)) >= 0) {
            count++;
            from += needle.length();
        }
        return count;
    }

    private static String oneLine(String text) {
        return text == null ? "" : text.replace('\n', ' ').replace('\r', ' ');
    }

    private static String stringList(List<String> items) {
        StringBuilder json = new StringBuilder("[");
        for (int index = 0; index < items.size(); index++) {
            if (index > 0) {
                json.append(",");
            }
            json.append(quote(items.get(index)));
        }
        return json.append("]").toString();
    }

    private static String quote(String text) {
        StringBuilder json = new StringBuilder("\"");
        for (int index = 0; index < text.length(); index++) {
            char letter = text.charAt(index);
            if (letter == '"' || letter == '\\') {
                json.append('\\').append(letter);
            } else if (letter < 0x20 || letter > 0x7e) {
                json.append(String.format("\\u%04x", (int) letter));
            } else {
                json.append(letter);
            }
        }
        return json.append("\"").toString();
    }
}
