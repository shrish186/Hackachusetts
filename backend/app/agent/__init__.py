"""LLM tool-calling agent. Orchestrates the engine and explains results.

The agent never computes risk, routes, or zone facts — tools do. Every factual
claim must carry a citation to a tool result (see .kiro/steering/product.md).
"""
