"""Tiny Molang interpreter (subset) to execute the shipped player.entity.json scripts and render-controller
part_visibility rules, so the FPS/CPS logic is tested exactly as written in the pack."""
import json, math, re, sys

TOK = re.compile(r"\s*(?:(\d+\.\d*|\.\d+|\d+)|([A-Za-z_][A-Za-z0-9_.]*)|'([^']*)'|(&&|\|\||==|!=|<=|>=|[-+*/()<>!?:,=;\[\]]))")


def tokenize(s):
    out, i = [], 0
    while i < len(s):
        m = TOK.match(s, i)
        if not m:
            if s[i:].strip() == "": break
            raise SyntaxError(f"bad char at {i}: {s[i:i+20]!r}")
        num, name, string, op = m.groups()
        out.append(("num", float(num)) if num else ("name", name.lower()) if name else ("str", string) if string is not None else ("op", op))
        i = m.end()
    return out


class P:
    def __init__(self, toks): self.t, self.i = toks, 0
    def peek(self): return self.t[self.i] if self.i < len(self.t) else ("eof", None)
    def eat(self, v=None):
        tok = self.peek()
        if v is not None and tok[1] != v: raise SyntaxError(f"expected {v}, got {tok}")
        self.i += 1; return tok
    def expr(self):
        c = self.orx()
        if self.peek()[1] == "?":
            self.eat("?"); a = self.expr()
            if self.peek()[1] == ":":
                self.eat(":"); b = self.expr()
            else:
                b = ("num", 0.0)
            return ("tern", c, a, b)
        return c
    def orx(self):
        l = self.andx()
        while self.peek()[1] == "||": self.eat(); l = ("||", l, self.andx())
        return l
    def andx(self):
        l = self.cmp()
        while self.peek()[1] == "&&": self.eat(); l = ("&&", l, self.cmp())
        return l
    def cmp(self):
        l = self.add()
        while self.peek()[1] in ("<", ">", "<=", ">=", "==", "!="): op = self.eat()[1]; l = (op, l, self.add())
        return l
    def add(self):
        l = self.mul()
        while self.peek()[1] in ("+", "-"): op = self.eat()[1]; l = (op, l, self.mul())
        return l
    def mul(self):
        l = self.un()
        while self.peek()[1] in ("*", "/"): op = self.eat()[1]; l = (op, l, self.un())
        return l
    def un(self):
        t = self.peek()
        if t[1] == "!": self.eat(); return ("!", self.un())
        if t[1] == "-": self.eat(); return ("neg", self.un())
        return self.atom()
    def atom(self):
        t = self.eat()
        if t[0] in ("num", "str"): return t
        if t[1] == "(":
            e = self.expr(); self.eat(")"); return e
        if t[0] == "name":
            if self.peek()[1] == "(":
                self.eat("("); args = []
                if self.peek()[1] != ")":
                    args.append(self.expr())
                    while self.peek()[1] == ",": self.eat(); args.append(self.expr())
                self.eat(")"); return ("call", t[1], args)
            return ("var", t[1])
        raise SyntaxError(f"unexpected {t}")


MATH = {"math.clamp": lambda x, a, b: min(max(x, a), b), "math.min": min, "math.max": max,
        "math.round": lambda x: float(math.floor(x + 0.5)), "math.floor": lambda x: float(math.floor(x)),
        "math.mod": lambda a, b: math.fmod(a, b), "math.sqrt": math.sqrt, "math.pow": math.pow,
        "math.sin": lambda x: math.sin(math.radians(x)), "math.cos": lambda x: math.cos(math.radians(x)),
        "math.abs": abs}


class Env:
    def __init__(self, queries): self.vars, self.q, self.unknown = {}, queries, set()
    def get(self, name):
        if name.startswith(("variable.", "v.")): return self.vars.get("variable." + name.split(".", 1)[1], 0.0)
        if name.startswith(("query.", "q.")):
            key = "query." + name.split(".", 1)[1]
            if key in self.q: return float(self.q[key])
            self.unknown.add(key); return 0.0
        raise NameError(name)
    def ev(self, n):
        k = n[0]
        if k in ("num", "str"): return n[1]
        if k == "var": return self.get(n[1])
        if k == "call":
            if n[1] in MATH: return float(MATH[n[1]](*[self.ev(a) for a in n[2]]))
            key = "query." + n[1].split(".", 1)[1]
            if key in self.q and callable(self.q[key]): return float(self.q[key](*[self.ev(a) for a in n[2]]))
            self.unknown.add(n[1]); return 0.0
        if k == "tern": return self.ev(n[2]) if self.ev(n[1]) != 0 else self.ev(n[3])
        if k == "!": return float(self.ev(n[1]) == 0)
        if k == "neg": return -self.ev(n[1])
        a = self.ev(n[1])
        if k == "&&": return float(a != 0 and self.ev(n[2]) != 0)
        if k == "||": return float(a != 0 or self.ev(n[2]) != 0)
        b = self.ev(n[2])
        return float({"<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b, "==": a == b, "!=": a != b}[k]) if k in ("<", ">", "<=", ">=", "==", "!=") \
            else {"+": a + b, "-": a - b, "*": a * b, "/": a / b if b else 0.0}[k]
    def run(self, stmt):
        stmt = stmt.strip().rstrip(";")
        m = re.match(r"^\s*((?:variable|v)\.[A-Za-z0-9_]+)\s*=(?!=)\s*(.+)$", stmt, re.S)
        if not m: raise SyntaxError("not an assignment: " + stmt[:60])
        p = P(tokenize(m.group(2))); val = self.ev(p.expr())
        if p.peek()[0] != "eof": raise SyntaxError("trailing tokens in: " + stmt[:80])
        self.vars["variable." + m.group(1).split(".", 1)[1]] = val


def parse_only(expr):
    p = P(tokenize(expr)); p.expr()
    if p.peek()[0] != "eof": raise SyntaxError("trailing tokens: " + expr[:80])
