"""Match coordinator-reviewed equivalent mutants to exact native source bytes.

Reviews are invalidated by any source change. A reason is mandatory; surviving
the cases alone is never evidence of equivalence.
"""
import hashlib
import re


def digest(source):
    return hashlib.sha256(source.encode()).hexdigest()


def validate(source, candidates, reviews):
    """Return exact reviewed identities and errors, including stale reviews."""
    if not isinstance(reviews, list):
        return {}, ["equivalent_mutants: expected an array"]
    source_hash = digest(source)
    available = {(line, operator, digest("\n".join(mutated) + "\n"))
                 for line, operator, mutated in candidates}
    accepted, errors = {}, []
    for number, review in enumerate(reviews):
        label = f"equivalent_mutants[{number}]"
        if not isinstance(review, dict):
            errors.append(f"{label}: expected an object")
            continue
        if not isinstance(review.get("reason"), str) or not review["reason"].strip():
            errors.append(f"{label}: a reviewed proof of equivalence is required")
            continue
        if review.get("source_sha256") != source_hash:
            errors.append(f"{label}: source hash is stale or missing")
            continue
        mutant_hash = review.get("mutant_sha256", "")
        if not isinstance(mutant_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", mutant_hash):
            errors.append(f"{label}: invalid mutant hash")
            continue
        line, operator = review.get("line"), review.get("operator")
        if not isinstance(line, int) or isinstance(line, bool) or not isinstance(operator, str):
            errors.append(f"{label}: line and operator are required")
            continue
        identity = (line, operator, mutant_hash)
        if identity not in available:
            errors.append(f"{label}: no generated mutant matches the review")
        elif identity in accepted:
            errors.append(f"{label}: duplicate review")
        else:
            accepted[identity] = review["reason"]
    return accepted, errors


def classify(results, reviewed):
    """Exclude only reviewed survivors; a killed or invalid review fails closed."""
    survivors, equivalent, errors = [], [], []
    for result in results:
        identity = (result["line"], result["operator"], result["mutant_sha256"])
        if identity in reviewed:
            if result["result"] != "survived":
                errors.append(f"reviewed equivalent mutant {result['operator']}@{result['line']} "
                              f"was {result['result']}")
            else:
                equivalent.append({**result, "reason": reviewed[identity]})
                continue
        if result["result"] == "survived":
            survivors.append(result)
    killed = sum(result["result"] == "killed" for result in results)
    valid = killed + len(survivors)
    return {"killed": killed, "survived": survivors, "equivalent": equivalent,
            "invalid": sum(result["result"] == "invalid" for result in results),
            "score": round(killed / valid, 3) if valid else None}, errors
