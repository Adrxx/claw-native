import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.charset.StandardCharsets;

// Explicit callback entry is observed in the original registration table.
// Operates only on the analysis database, never the input executable bytes.
public class RecoverRegisteredCallback extends GhidraScript {
    @Override public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 3) throw new IllegalArgumentException("ADDRESS[,ADDRESS...] NAME OUTPUT");
        String originalHash = "350b8d51e1cd52037cd31a7722197a815e4206e7d3052ec632465f1354726263";
        if (!originalHash.equalsIgnoreCase(currentProgram.getExecutableSHA256()))
            throw new IllegalStateException("Registered callback addresses require fingerprinted original v1.0");
        DecompInterface decompiler = new DecompInterface();
        try {
            if (!decompiler.openProgram(currentProgram)) throw new IllegalStateException(decompiler.getLastMessage());
            StringBuilder output = new StringBuilder();
            for (String address : args[0].split(",")) {
                Address entry = toAddr(address);
                disassemble(entry);
                Function function = getFunctionAt(entry);
                Function containing = getFunctionContaining(entry);
                if (function == null && containing != null)
                    throw new IllegalStateException("Requested address is inside " + containing.getName() + " at " + containing.getEntryPoint());
                if (function == null) function = createFunction(entry, args[1] + "_" + address.replace("0x", ""));
                if (function == null) throw new IllegalStateException("Cannot define callback at " + entry);
                DecompileResults result = decompiler.decompileFunction(function, 90, monitor);
                if (!result.decompileCompleted()) throw new IllegalStateException(result.getErrorMessage());
                output.append("\n// Original v1.0 entry: ").append(entry).append("\n").append(result.getDecompiledFunction().getC());
                // Keep completed entries if a later requested address is invalid.
                Files.writeString(Path.of(args[2]), output.toString(), StandardCharsets.UTF_8);
                println("Recovered " + function.getName() + " at " + entry + ", " + function.getBody().getNumAddresses() + " bytes");
            }
        } finally { decompiler.dispose(); }
    }
}
