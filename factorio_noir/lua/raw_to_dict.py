#!/usr/local/bin/python3

import math
import pickle
import operator

import luaparser.ast
import luaparser.astnodes as lua
from luaparser.utils.visitor import visitor


UNARY_OP_TABLE = {
    lua.UMinusOp: operator.neg,
    lua.UBNotOp: operator.inv,
    lua.ULNotOp: operator.not_,
}

class LuaDictVisitor:
    """Converts a table declaration into a python dict """
    @visitor(lua.Nil)
    def visit(self, node):
        return None

    @visitor(lua.TrueExpr)
    def visit(self, node):
        return True

    @visitor(lua.FalseExpr)
    def visit(self, node):
        return False

    @visitor(lua.String)
    def visit(self, node):
        return node.s

    @visitor(lua.Number)
    def visit(self, node):
        return float(node.n)

    @visitor(lua.Name)
    def visit(self, node):
        return node.id

    @visitor(lua.UnaryOp)
    def visit(self, node):
        return UNARY_OP_TABLE[type(node)](self.visit(node.operand))

    @visitor(lua.FloatDivOp)
    def visit(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)

        # Serpent will serialize inifinity as a division by zero
        if right == 0.0:
            return left * math.inf
        return left / right

    @visitor(lua.Table)
    def visit(self, node):
        table = {}
        for field in node.fields:
            table[self.visit(field.key)] = self.visit(field.value)
        return table

if __name__ == '__main__':
    print("Parsing raw.txt, this will take a while")
    with open("raw.txt") as f:
        root = luaparser.ast.parse(f.read())

    # raw = { ... parses as
    # Chunk.body -> Block.body -> list[0] -> Assign.values -> list[0] -> Table
    print("converting to dict")
    table = root.body.body[0].values[0]
    converted = LuaDictVisitor().visit(table)

    print("writing to raw.pickle")
    with open("raw.pickle", "wb") as output:
        pickle.dump(converted, output)
