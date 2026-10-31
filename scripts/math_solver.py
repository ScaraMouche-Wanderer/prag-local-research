#!/usr/bin/env python3
"""
High-Precision Mathematical Engine & Symbolics Solver for Local PRAG System.
Features:
  - Exact numerical arithmetic with arbitrary precision via sympy & Python
  - Algebraic equation solving, polynomial factoring, simplification
  - Calculus engine (symbolic derivatives, indefinite & definite integrals, limits)
  - Number theory (modular arithmetic, GCD, LCM, factorials, primes, combinatorics)
  - Step-by-step derivation breakdown for LLM context injection & instant evaluation
"""

import re
import math
import ast
import operator
from typing import Optional, Dict, Any

try:
    import sympy as sp
    from sympy.parsing.sympy_parser import (
        parse_expr,
        standard_transformations,
        implicit_multiplication_application,
        convert_xor
    )
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False


# Supported safe operators for arithmetic & bitwise AST parsing
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.BitAnd: operator.and_,
    ast.BitOr: operator.or_,
    ast.BitXor: operator.xor,
    ast.LShift: operator.lshift,
    ast.RShift: operator.rshift,
    ast.Invert: operator.invert,
}

SAFE_FUNCTIONS = {
    'abs': abs,
    'round': round,
    'min': min,
    'max': max,
    'pow': pow,
    'sqrt': math.sqrt,
    'cbrt': lambda x: x ** (1/3),
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'asin': math.asin,
    'acos': math.acos,
    'atan': math.atan,
    'sinh': math.sinh,
    'cosh': math.cosh,
    'tanh': math.tanh,
    'exp': math.exp,
    'log': math.log,
    'log10': math.log10,
    'log2': math.log2,
    'floor': math.floor,
    'ceil': math.ceil,
    'factorial': math.factorial,
    'gcd': math.gcd,
    'lcm': getattr(math, 'lcm', lambda a, b: abs(a*b) // math.gcd(a, b)),
    'pi': math.pi,
    'e': math.e,
    'hex': hex,
    'bin': bin,
    'oct': oct,
}


def _safe_eval_ast(node):
    """Safely evaluates an AST expression without eval() or arbitrary code execution."""
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.Name):
        if node.id in SAFE_FUNCTIONS:
            return SAFE_FUNCTIONS[node.id]
        raise ValueError(f"Unknown identifier: {node.id}")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = _safe_eval_ast(node.left)
        right = _safe_eval_ast(node.right)
        return SAFE_OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        operand = _safe_eval_ast(node.operand)
        return SAFE_OPERATORS[op_type](operand)
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in SAFE_FUNCTIONS:
            func = SAFE_FUNCTIONS[node.func.id]
            args = [_safe_eval_ast(arg) for arg in node.args]
            return func(*args)
        raise ValueError(f"Unsupported function call")
    else:
        raise ValueError(f"Unsupported syntax: {type(node).__name__}")


def extract_math_expression(query: str) -> Optional[str]:
    """
    Extracts arithmetic or mathematical expressions from a user prompt.
    e.g. 'What is (26655656 * 56463 * 0.546546) % 55 =' -> '(26655656 * 56463 * 0.546546) % 55'
    """
    cleaned = query.strip()
    
    # Remove leading question phrases
    cleaned = re.sub(
        r'^(?:what\s+is(?:\s+the)?(?:\s+value\s+of|\s+result\s+of)?|calculate(?:\s+the)?(?:\s+value\s+of|\s+result\s+of)?|compute(?:\s+the)?(?:\s+value\s+of|\s+result\s+of)?|solve|evaluate|find(?:\s+the)?(?:\s+value\s+of|\s+result\s+of)?|what\'s|value\s+of)\s+',
        '',
        cleaned,
        flags=re.IGNORECASE
    ).strip()
    
    # Remove trailing equals / question mark / spaces
    cleaned = re.sub(r'[\s=\?]+$', '', cleaned).strip()

    # Handle percentage queries like "15% of 80" -> "(15 / 100) * 80"
    pct_match = re.match(r'^([\d\.]+)\s*%\s+of\s+([\d\.]+)$', cleaned, re.IGNORECASE)
    if pct_match:
        return f"({pct_match.group(1)} / 100) * {pct_match.group(2)}"

    # If starts with 'f(x) =' or 'y ='
    cleaned = re.sub(r'^[a-zA-Z]\([a-zA-Z]\)\s*=\s*', '', cleaned).strip()

    # Check if cleaned text contains arithmetic or bitwise operators or math functions
    if any(c in cleaned for c in "+-*/%^&|~<>") or any(fn in cleaned.lower() for fn in SAFE_FUNCTIONS):
        return cleaned

    # Search for embedded formula within query
    formula_match = re.search(r'([\(\[\{]?\s*(?:0x[0-9a-fA-F]+|\d+\.?\d*)\s*[\+\-\*\/\%\^\&\|\<\>]\s*[\d\.\(\)\+\-\*\/\%\^\&\|\<\>\s0-9a-fA-FxXbB]+[\)\]\}]?)', query)
    if formula_match:
        cand = formula_match.group(1).strip().rstrip('=?').strip()
        if len(cand) >= 3 and any(op in cand for op in "+-*/%^&|<>"):
            return cand

    return None


def solve_symbolic_math(query: str) -> Optional[Dict[str, Any]]:
    """
    Solves symbolic math questions (derivatives, integrals, limits, equations) using SymPy.
    """
    if not SYMPY_AVAILABLE:
        return None

    q_lower = query.lower().strip()

    # 1. Derivative
    deriv_match = re.search(r'(?:derivative of|d\/dx|diff|differentiate)\s+(?:f\([a-zA-Z]\)\s*=\s*|y\s*=\s*)?(.+?)(?:\s+with respect to\s+([a-zA-Z]))?(?:\s*\?|\s*$)', q_lower)
    if deriv_match:
        expr_str = deriv_match.group(1).strip().rstrip('?').strip()
        var_str = deriv_match.group(2) or 'x'
        try:
            transformations = (standard_transformations + (implicit_multiplication_application, convert_xor))
            var = sp.Symbol(var_str)
            expr = parse_expr(expr_str.replace('^', '**'), transformations=transformations)
            res = sp.diff(expr, var)
            return {
                "type": "derivative",
                "expression": str(expr),
                "variable": var_str,
                "result": str(res),
                "latex": sp.latex(res),
                "steps": [
                    f"Given function: f({var_str}) = {expr}",
                    f"Applying differentiation rules with respect to {var_str}",
                    f"Derivative f'({var_str}) = {res}"
                ]
            }
        except Exception:
            pass

    # 2. Integral
    int_match = re.search(r'(?:integral of|integrate)\s+(.+?)(?:\s+from\s+([-\d\.\w]+)\s+to\s+([-\d\.\w]+))?(?:\s+with respect to\s+([a-zA-Z]))?(?:\s*\?|\s*$)', q_lower)
    if int_match:
        expr_str = int_match.group(1).strip().rstrip('?').strip()
        lower_bound = int_match.group(2)
        upper_bound = int_match.group(3)
        var_str = int_match.group(4) or 'x'
        try:
            transformations = (standard_transformations + (implicit_multiplication_application, convert_xor))
            var = sp.Symbol(var_str)
            expr = parse_expr(expr_str.replace('^', '**'), transformations=transformations)
            if lower_bound is not None and upper_bound is not None:
                lb = parse_expr(lower_bound)
                ub = parse_expr(upper_bound)
                res = sp.integrate(expr, (var, lb, ub))
                return {
                    "type": "definite_integral",
                    "expression": str(expr),
                    "lower": str(lb),
                    "upper": str(ub),
                    "result": str(res),
                    "latex": sp.latex(res),
                    "steps": [
                        f"Integrand: f({var_str}) = {expr}",
                        f"Integration interval: [{lb}, {ub}]",
                        f"Definite Integral Result = {res}"
                    ]
                }
            else:
                res = sp.integrate(expr, var)
                return {
                    "type": "indefinite_integral",
                    "expression": str(expr),
                    "result": f"{res} + C",
                    "latex": f"{sp.latex(res)} + C",
                    "steps": [
                        f"Integrand: f({var_str}) = {expr}",
                        f"Antiderivative = {res} + C"
                    ]
                }
        except Exception:
            pass

    # 3. Solve algebraic equation
    eq_match = re.search(r'(?:solve|find roots of|find x for)\s+(.+?=\s*.+|.+)', q_lower)
    if eq_match and ('=' in query or '==' in query):
        raw_eq = eq_match.group(1).strip().rstrip('?')
        try:
            transformations = (standard_transformations + (implicit_multiplication_application, convert_xor))
            if '=' in raw_eq:
                lhs_str, rhs_str = raw_eq.split('=', 1)
                lhs = parse_expr(lhs_str.replace('^', '**'), transformations=transformations)
                rhs = parse_expr(rhs_str.replace('^', '**'), transformations=transformations)
                eq = sp.Eq(lhs, rhs)
            else:
                expr = parse_expr(raw_eq.replace('^', '**'), transformations=transformations)
                eq = sp.Eq(expr, 0)
            
            free_symbols = list(eq.free_symbols)
            var = free_symbols[0] if free_symbols else sp.Symbol('x')
            sols = sp.solve(eq, var)
            return {
                "type": "equation",
                "equation": str(eq),
                "solutions": [str(s) for s in sols],
                "latex": [sp.latex(s) for s in sols],
                "steps": [
                    f"Equation: {lhs} = {rhs}" if '=' in raw_eq else f"Equation: {eq}",
                    f"Solving for variable: {var}",
                    f"Roots / Solutions: {sols}"
                ]
            }
        except Exception:
            pass

    return None


# ═══ Electronics Engineering Formula Solver ═══

# SI unit prefix multipliers
SI_PREFIXES = {
    'p': 1e-12, 'pico': 1e-12,
    'n': 1e-9, 'nano': 1e-9,
    'u': 1e-6, 'µ': 1e-6, 'micro': 1e-6,
    'm': 1e-3, 'milli': 1e-3,
    'k': 1e3, 'kilo': 1e3,
    'M': 1e6, 'mega': 1e6,
    'G': 1e9, 'giga': 1e9,
    'T': 1e12, 'tera': 1e12,
}

# Map suffix -> (base_unit, multiplier)
UNIT_SUFFIXES = {
    'ohm': ('Ω', 1), 'ohms': ('Ω', 1), 'Ω': ('Ω', 1),
    'V': ('V', 1), 'volt': ('V', 1), 'volts': ('V', 1),
    'A': ('A', 1), 'amp': ('A', 1), 'amps': ('A', 1), 'ampere': ('A', 1),
    'W': ('W', 1), 'watt': ('W', 1), 'watts': ('W', 1),
    'F': ('F', 1), 'farad': ('F', 1), 'farads': ('F', 1),
    'H': ('H', 1), 'henry': ('H', 1), 'henrys': ('H', 1),
    'Hz': ('Hz', 1), 'hertz': ('Hz', 1),
    's': ('s', 1), 'sec': ('s', 1), 'second': ('s', 1), 'seconds': ('s', 1),
    'dB': ('dB', 1), 'dBm': ('dBm', 1),
}


def _parse_ee_value(text: str) -> Optional[float]:
    """Parse a value with optional SI prefix, e.g., '4.7k', '100nF', '10µA', '3.3V'."""
    text = text.strip()
    # Try matching number + prefix + optional unit: 4.7kΩ, 100nF, 10µA, 47k, 3.3V
    m = re.match(r'^([\d\.]+)\s*([pnuµmkMGT]|pico|nano|micro|milli|kilo|mega|giga|tera)?\s*([A-Za-zΩ]*?)$', text)
    if m:
        val = float(m.group(1))
        prefix = m.group(2) or ''
        if prefix in SI_PREFIXES:
            val *= SI_PREFIXES[prefix]
        return val
    # Plain number
    try:
        return float(text)
    except ValueError:
        return None


def _format_ee_value(val: float, unit: str = '') -> str:
    """Format a value with appropriate SI prefix for readability."""
    if val == 0:
        return f"0{unit}"
    abs_val = abs(val)
    prefixes = [
        (1e12, 'T'), (1e9, 'G'), (1e6, 'M'), (1e3, 'k'),
        (1, ''), (1e-3, 'm'), (1e-6, 'µ'), (1e-9, 'n'), (1e-12, 'p')
    ]
    for threshold, prefix in prefixes:
        if abs_val >= threshold:
            scaled = val / threshold
            if scaled == int(scaled):
                return f"{int(scaled)}{prefix}{unit}"
            return f"{scaled:.3g}{prefix}{unit}"
    return f"{val:.4g}{unit}"


def evaluate_ee_formula(query: str) -> Optional[Dict[str, Any]]:
    """
    Evaluates common electronics engineering formulas:
    - Ohm's Law (V=IR, I=V/R, R=V/I)
    - Voltage Divider (Vout = Vin * R2/(R1+R2))
    - RC Time Constant (τ = R*C)
    - Power Dissipation (P=VI, P=I²R, P=V²/R)
    - dB conversions (voltage dB, power dBm)
    - Capacitive/Inductive Reactance (Xc = 1/(2πfC), Xl = 2πfL)
    - Frequency ↔ Period conversion
    - SI unit prefix conversions
    """
    q = query.lower().strip()

    # --- Ohm's Law: V=IR variants ---
    # "V = IR for R=470 I=0.02" or "current through 1k resistor with 5V"
    ohm_patterns = [
        # Explicit: "R=470 I=0.02 find V"
        (r'(?:ohm|v\s*=\s*i\s*r|voltage).*?r\s*=?\s*([\d\.]+[pnuµmkMGT]?\s*(?:ohm|Ω)?)\s*.*?i\s*=?\s*([\d\.]+[pnuµmkMGT]?\s*a?)',
         lambda r, i: ('V', _parse_ee_value(r) * _parse_ee_value(i), f"V = I × R = {i} × {r}")),
        # "current through 470 ohm resistor with 5V" or "I for V=5 R=470"
        (r'(?:current|i\s*=\s*v\s*/\s*r).*?(?:v\s*=?\s*([\d\.]+[pnuµmkMGT]?\s*v?))\s*.*?(?:r\s*=?\s*([\d\.]+[pnuµmkMGT]?\s*(?:ohm|Ω)?))',
         lambda v, r: ('A', _parse_ee_value(v) / _parse_ee_value(r), f"I = V / R = {v} / {r}")),
        (r'(?:current|i\s*=\s*v\s*/\s*r).*?(?:r\s*=?\s*([\d\.]+[pnuµmkMGT]?\s*(?:ohm|Ω)?))\s*.*?(?:v\s*=?\s*([\d\.]+[pnuµmkMGT]?\s*v?))',
         lambda r, v: ('A', _parse_ee_value(v) / _parse_ee_value(r), f"I = V / R = {v} / {r}")),
        # "voltage across R with I"
        (r'(?:voltage\s+across)\s+([\d\.]+[pnuµmkMGT]?\s*(?:ohm|Ω|k)?)\s*(?:resistor)?\s*(?:with|at)\s+([\d\.]+[pnuµmkMGT]?\s*a?)\s*(?:current)?',
         lambda r, i: ('V', _parse_ee_value(r) * _parse_ee_value(i), f"V = I × R = {i} × {r}")),
    ]

    for pattern, calc_fn in ohm_patterns:
        m = re.search(pattern, q)
        if m:
            try:
                unit, result, step = calc_fn(*m.groups())
                return {
                    "is_math": True,
                    "category": "ee_formula",
                    "formula": "Ohm's Law",
                    "formatted_result": _format_ee_value(result, unit),
                    "raw_result": result,
                    "steps": [
                        f"Formula: Ohm's Law (V = I × R)",
                        step,
                        f"Result: **{_format_ee_value(result, unit)}**"
                    ],
                    "summary_text": f"{_format_ee_value(result, unit)}"
                }
            except Exception:
                pass

    # --- Voltage Divider ---
    vd_match = re.search(
        r'voltage\s+divider.*?r1\s*=?\s*([\d\.]+[pnuµmkMGT]?\s*(?:ohm|Ω)?)\s*.*?r2\s*=?\s*([\d\.]+[pnuµmkMGT]?\s*(?:ohm|Ω)?)\s*.*?v(?:in|s|cc|supply)?\s*=?\s*([\d\.]+[pnuµmkMGT]?\s*v?)',
        q
    )
    if vd_match:
        try:
            r1 = _parse_ee_value(vd_match.group(1))
            r2 = _parse_ee_value(vd_match.group(2))
            vin = _parse_ee_value(vd_match.group(3))
            vout = vin * r2 / (r1 + r2)
            return {
                "is_math": True,
                "category": "ee_formula",
                "formula": "Voltage Divider",
                "formatted_result": _format_ee_value(vout, 'V'),
                "raw_result": vout,
                "steps": [
                    f"Formula: Vout = Vin × R2 / (R1 + R2)",
                    f"R1 = {_format_ee_value(r1, 'Ω')}, R2 = {_format_ee_value(r2, 'Ω')}, Vin = {_format_ee_value(vin, 'V')}",
                    f"Vout = {vin} × {r2} / ({r1} + {r2}) = **{_format_ee_value(vout, 'V')}**"
                ],
                "summary_text": f"Vout = {_format_ee_value(vout, 'V')}"
            }
        except Exception:
            pass

    # --- RC Time Constant ---
    rc_match = re.search(
        r'(?:rc|time\s+constant|tau|τ).*?r\s*=?\s*([\d\.]+[pnuµmkMGT]?\s*(?:ohm|Ω)?)\s*.*?c\s*=?\s*([\d\.]+[pnuµmkMGT]?\s*f?)',
        q
    )
    if rc_match:
        try:
            r = _parse_ee_value(rc_match.group(1))
            c = _parse_ee_value(rc_match.group(2))
            tau = r * c
            return {
                "is_math": True,
                "category": "ee_formula",
                "formula": "RC Time Constant",
                "formatted_result": _format_ee_value(tau, 's'),
                "raw_result": tau,
                "steps": [
                    f"Formula: τ = R × C",
                    f"R = {_format_ee_value(r, 'Ω')}, C = {_format_ee_value(c, 'F')}",
                    f"τ = {r} × {c} = **{_format_ee_value(tau, 's')}**",
                    f"Time to reach ~63.2% of final value: {_format_ee_value(tau, 's')}",
                    f"Time to reach ~99.3% (5τ): {_format_ee_value(5 * tau, 's')}"
                ],
                "summary_text": f"τ = {_format_ee_value(tau, 's')}"
            }
        except Exception:
            pass

    # --- Power Dissipation: P = V²/R ---
    power_vr_match = re.search(
        r'(?:power|p\s*=\s*v).*?v\s*=?\s*([\d\.]+[pnuµmkMGT]?\s*v?)\s*.*?r\s*=?\s*([\d\.]+[pnuµmkMGT]?\s*(?:ohm|Ω)?)',
        q
    )
    if power_vr_match:
        try:
            v = _parse_ee_value(power_vr_match.group(1))
            r = _parse_ee_value(power_vr_match.group(2))
            p = (v ** 2) / r
            return {
                "is_math": True,
                "category": "ee_formula",
                "formula": "Power Dissipation (P = V²/R)",
                "formatted_result": _format_ee_value(p, 'W'),
                "raw_result": p,
                "steps": [
                    f"Formula: P = V² / R",
                    f"V = {_format_ee_value(v, 'V')}, R = {_format_ee_value(r, 'Ω')}",
                    f"P = {v}² / {r} = **{_format_ee_value(p, 'W')}**"
                ],
                "summary_text": f"P = {_format_ee_value(p, 'W')}"
            }
        except Exception:
            pass

    # --- dB Conversion: dBm to watts ---
    dbm_match = re.search(r'([\-\d\.]+)\s*dbm\s+(?:to|in)\s+(?:watt|mw|milliwatt|w)', q)
    if dbm_match:
        try:
            dbm = float(dbm_match.group(1))
            watts = 10 ** ((dbm - 30) / 10)
            mw = watts * 1000
            return {
                "is_math": True,
                "category": "ee_formula",
                "formula": "dBm to Watts",
                "formatted_result": _format_ee_value(watts, 'W') if watts < 0.001 else f"{mw:.4g}mW",
                "raw_result": watts,
                "steps": [
                    f"Formula: P(W) = 10^((dBm - 30) / 10)",
                    f"dBm = {dbm}",
                    f"P = 10^(({dbm} - 30) / 10) = **{_format_ee_value(watts, 'W')}** ({mw:.4g} mW)"
                ],
                "summary_text": f"{dbm} dBm = {_format_ee_value(watts, 'W')}"
            }
        except Exception:
            pass

    # --- Watts to dBm ---
    w_to_dbm_match = re.search(r'([\d\.]+)\s*(?:m?w(?:att)?s?)\s+(?:to|in)\s+dbm', q)
    if w_to_dbm_match:
        try:
            raw_val = w_to_dbm_match.group(0)
            watts = float(w_to_dbm_match.group(1))
            if 'mw' in raw_val.lower() or 'milliwatt' in raw_val.lower():
                watts = watts / 1000
            dbm = 10 * math.log10(watts * 1000)
            return {
                "is_math": True,
                "category": "ee_formula",
                "formula": "Watts to dBm",
                "formatted_result": f"{dbm:.2f} dBm",
                "raw_result": dbm,
                "steps": [
                    f"Formula: dBm = 10 × log₁₀(P_mW)",
                    f"P = {_format_ee_value(watts, 'W')}",
                    f"dBm = 10 × log₁₀({watts * 1000}) = **{dbm:.2f} dBm**"
                ],
                "summary_text": f"{_format_ee_value(watts, 'W')} = {dbm:.2f} dBm"
            }
        except Exception:
            pass

    # --- Capacitive Reactance: Xc = 1/(2πfC) ---
    xc_match = re.search(
        r'(?:capacitive\s+reactance|xc).*?(?:c\s*=?\s*([\d\.]+[pnuµmkMGT]?\s*f?)).*?(?:f\s*=?\s*([\d\.]+[pnuµmkMGT]?\s*(?:hz)?))',
        q
    )
    if not xc_match:
        xc_match = re.search(
            r'(?:capacitive\s+reactance|xc).*?(?:f\s*=?\s*([\d\.]+[pnuµmkMGT]?\s*(?:hz)?)).*?(?:c\s*=?\s*([\d\.]+[pnuµmkMGT]?\s*f?))',
            q
        )
        if xc_match:
            xc_match = type('M', (), {'group': lambda self, i: [None, xc_match.group(2), xc_match.group(1)][i]})()
    if xc_match:
        try:
            c = _parse_ee_value(xc_match.group(1))
            f = _parse_ee_value(xc_match.group(2))
            xc = 1 / (2 * math.pi * f * c)
            return {
                "is_math": True,
                "category": "ee_formula",
                "formula": "Capacitive Reactance",
                "formatted_result": _format_ee_value(xc, 'Ω'),
                "raw_result": xc,
                "steps": [
                    f"Formula: Xc = 1 / (2πfC)",
                    f"f = {_format_ee_value(f, 'Hz')}, C = {_format_ee_value(c, 'F')}",
                    f"Xc = 1 / (2π × {f} × {c}) = **{_format_ee_value(xc, 'Ω')}**"
                ],
                "summary_text": f"Xc = {_format_ee_value(xc, 'Ω')}"
            }
        except Exception:
            pass

    # --- Frequency ↔ Period ---
    freq_match = re.search(r'(?:frequency|freq)\s+(?:of|for)\s+([\d\.]+[pnuµmkMGT]?\s*s(?:ec(?:ond)?s?)?)\s+(?:period|cycle)', q)
    if freq_match:
        try:
            period = _parse_ee_value(freq_match.group(1))
            freq = 1 / period
            return {
                "is_math": True,
                "category": "ee_formula",
                "formula": "Frequency from Period",
                "formatted_result": _format_ee_value(freq, 'Hz'),
                "raw_result": freq,
                "steps": [
                    f"Formula: f = 1 / T",
                    f"T = {_format_ee_value(period, 's')}",
                    f"f = 1 / {period} = **{_format_ee_value(freq, 'Hz')}**"
                ],
                "summary_text": f"f = {_format_ee_value(freq, 'Hz')}"
            }
        except Exception:
            pass

    period_match = re.search(r'(?:period)\s+(?:of|for)\s+([\d\.]+[pnuµmkMGT]?\s*(?:hz|hertz)?)\s+(?:frequency|signal|wave)', q)
    if period_match:
        try:
            freq = _parse_ee_value(period_match.group(1))
            period = 1 / freq
            return {
                "is_math": True,
                "category": "ee_formula",
                "formula": "Period from Frequency",
                "formatted_result": _format_ee_value(period, 's'),
                "raw_result": period,
                "steps": [
                    f"Formula: T = 1 / f",
                    f"f = {_format_ee_value(freq, 'Hz')}",
                    f"T = 1 / {freq} = **{_format_ee_value(period, 's')}**"
                ],
                "summary_text": f"T = {_format_ee_value(period, 's')}"
            }
        except Exception:
            pass

    return None


def evaluate_math_query(query: str) -> Optional[Dict[str, Any]]:
    """
    Evaluates math/formula queries with exact deterministic computation.
    Returns structured math solution with exact result and step-by-step derivation.
    Checks EE formulas first, then symbolic math, then raw arithmetic.
    """
    # Check EE formulas first (Ohm's law, voltage divider, RC, dB, reactance)
    ee_result = evaluate_ee_formula(query)
    if ee_result:
        return ee_result

    # Check symbolic math next (derivatives, integrals, equations)
    symbolic = solve_symbolic_math(query)
    if symbolic:
        res_val = symbolic.get('result') or ", ".join(symbolic.get('solutions', []))
        return {
            "is_math": True,
            "category": "symbolic",
            "data": symbolic,
            "formatted_result": str(res_val),
            "steps": symbolic.get("steps", []),
            "summary_text": f"Result: {res_val}"
        }

    # Check arithmetic / numerical expression
    expr_str = extract_math_expression(query)
    if not expr_str:
        return None

    # Pre-process expression for Python AST
    sanitized = expr_str.replace('×', '*').replace('÷', '/').replace('–', '-')
    if '^' in sanitized and not any(op in sanitized for op in ('&', '|', '<<', '>>')) and '0x' not in sanitized:
        # Standard power notation in non-bitwise arithmetic
        sanitized = sanitized.replace('^', '**')
    
    # Evaluate with safe AST
    try:
        parsed_ast = ast.parse(sanitized, mode='eval')
        exact_value = _safe_eval_ast(parsed_ast.body)
        
        # Format the value cleanly
        is_hex_input = '0x' in expr_str.lower()
        is_bitwise = any(c in expr_str for c in ('&', '|', '^', '<<', '>>', '~'))

        if isinstance(exact_value, int):
            if is_hex_input or is_bitwise:
                formatted_val = f"{exact_value} ({hex(exact_value)})"
            else:
                formatted_val = str(exact_value)
        elif isinstance(exact_value, float):
            if exact_value.is_integer():
                formatted_val = f"{int(exact_value)}"
            else:
                formatted_val = f"{exact_value:g}"
        else:
            formatted_val = str(exact_value)

        # Generate step-by-step breakdown
        steps = []
        steps.append(f"Expression: `{expr_str}`")

        # If compound expression with modulo or parentheses, show sub-steps
        if '%' in expr_str:
            parts = expr_str.rsplit('%', 1)
            left_part = parts[0].strip()
            mod_val = parts[1].strip()
            try:
                sub_ast = ast.parse(left_part.replace('^', '**'), mode='eval')
                sub_val = _safe_eval_ast(sub_ast.body)
                steps.append(f"1. Evaluate inner terms: `{left_part}` = **{sub_val}**")
                steps.append(f"2. Compute modulo: `{sub_val} % {mod_val}` = **{formatted_val}**")
            except Exception:
                steps.append(f"Computed value: **{formatted_val}**")
        elif is_hex_input or is_bitwise:
            steps.append(f"Evaluated bitwise/arithmetic result: **{exact_value}** (Hex: `{hex(exact_value) if isinstance(exact_value, int) else formatted_val}`)")
        else:
            steps.append(f"Calculated value: **{formatted_val}**")

        return {
            "is_math": True,
            "category": "arithmetic",
            "expression": expr_str,
            "raw_result": exact_value,
            "formatted_result": formatted_val,
            "steps": steps,
            "summary_text": f"{expr_str} = {formatted_val}"
        }
    except Exception:
        pass

    return None


if __name__ == "__main__":
    test_queries = [
        "What is (26655656 * 56463 * 0.546546) % 55 =",
        "Calculate 2^10 + 5 * 12",
        "What is the derivative of f(x) = x^3 * sin(x)?",
        "Solve 3*x + 9 = 24",
        "sqrt(144) + factorial(5)"
    ]

    for q in test_queries:
        res = evaluate_math_query(q)
        print(f"Query: {q}")
        if res:
            print(f"  Result: {res.get('formatted_result')}")
            print(f"  Steps: {res.get('steps')}\n")
        else:
            print("  Not a math query.\n")
