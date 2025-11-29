"""
SMT-LIB specific utilities for Z3 solving and preprocessing.
"""

import re
import time
from typing import Dict, List, Tuple, Any

try:
    import z3
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False


def preprocess_smt2(smt2_content: str) -> str:
    """
    Preprocess SMT2 content to fix common issues.

    Args:
        smt2_content: Original SMT2 content.

    Returns:
        Preprocessed SMT2 content.
    """
    # Replace unsupported QF_BOOL logic with QF_UF
    content = re.sub(r"\(set-logic\s+QF_BOOL\)", "(set-logic QF_UF)", smt2_content)

    # Ensure proper spacing for better parsing
    content = re.sub(r"\(\s+", "(", content)
    content = re.sub(r"\s+\)", ")", content)

    return content


def solve_with_z3_api(program: str, program_index: int, timeout: int = 30) -> Dict[str, Any]:
    """
    Solve an SMT2 problem using Z3's Python API.

    Args:
        program: Content of the SMT2 file.
        program_index: Index of the program for tracking.
        timeout: Timeout in seconds.

    Returns:
        Dictionary with result information.
    """
    if not Z3_AVAILABLE:
        return {
            "program_index": program_index,
            "result": "error",
            "output": "Z3 not available",
            "time_taken": 0,
        }

    fixed_content = preprocess_smt2(program)

    result = {
        "program_index": program_index,
        "result": "unknown",
        "output": "",
        "time_taken": 0,
    }

    start_time = time.time()

    try:
        z3.set_param("timeout", timeout * 1000)
        solver = z3.Solver()

        try:
            formula = z3.parse_smt2_string(fixed_content)
            solver.add(formula)
        except z3.Z3Exception:
            solver = z3.Solver()
            solver.from_string(fixed_content)

        check_result = solver.check()

        if check_result == z3.sat:
            result["result"] = "sat"
            result["output"] = "sat"
        elif check_result == z3.unsat:
            result["result"] = "unsat"
            result["output"] = "unsat"
        else:
            result["result"] = "unknown"
            result["output"] = str(check_result)

    except z3.Z3Exception as e:
        error_message = str(e)
        if "unsupported" in error_message.lower():
            try:
                ctx = z3.Context()
                solver = z3.Solver(ctx=ctx)
                modified_content = re.sub(
                    r"\(set-logic [^)]*\)", "(set-logic ALL)", fixed_content
                )
                solver.from_string(modified_content)
                check_result = solver.check()

                if check_result == z3.sat:
                    result["result"] = "sat"
                    result["output"] = "sat"
                elif check_result == z3.unsat:
                    result["result"] = "unsat"
                    result["output"] = "unsat"
                else:
                    result["result"] = "unknown"
                    result["output"] = "unknown after logic fix"
            except Exception:
                result["result"] = "error"
                result["output"] = f"Error: {error_message}"
        else:
            result["result"] = "error"
            result["output"] = f"Error: {error_message}"
    except Exception as e:
        result["result"] = "error"
        result["output"] = f"Error: {str(e)}"

    result["time_taken"] = time.time() - start_time
    return result


def analyze_z3_results(programs: List[str]) -> Tuple[Dict[str, int], List[Dict[str, Any]]]:
    """
    Run Z3 on each SMT2 program and analyze the results.

    Args:
        programs: List of SMT2 program contents.

    Returns:
        Tuple of (summary dict, detailed results list).
    """
    results = {"sat": 0, "unsat": 0, "unknown": 0, "errors": 0}
    detailed_results = []
    timeouts = [10, 30, 60]

    for i, program in enumerate(programs):
        final_result = None

        for timeout_idx, timeout in enumerate(timeouts):
            result = solve_with_z3_api(program, i, timeout)

            if result["result"] in ["sat", "unsat"]:
                final_result = result
                break

            if timeout_idx == len(timeouts) - 1:
                final_result = result

        result_type = final_result["result"]
        if result_type == "error":
            results["errors"] += 1
        else:
            results[result_type] = results.get(result_type, 0) + 1

        detailed_results.append(final_result)

    return results, detailed_results
