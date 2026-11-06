from typing import TypedDict
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

# Connection to LiteLLM Gateway
config = {"api_key": "sk-eeL48ovOOidT93Pyk8-79g", "base_url": "http://192.168.4.70:4000/v1"}
coder = ChatOpenAI(model="cluster-coder", **config)
reviewer = ChatOpenAI(model="cluster-reviewer", **config)

class State(TypedDict):
    task: str; code: str; feedback: str; loops: int; approved: bool

def do_code(s: State):
    p = ChatPromptTemplate.from_template("Task: {task}\nCode: {code}\nFix: {feedback}")
    return {"code": (p | coder).invoke(s).content, "loops": s["loops"] + 1}

def do_review(s: State):
    f = (ChatPromptTemplate.from_template("Task: {task}\nReview: {code}") | reviewer).invoke(s).content
    return {"feedback": f, "approved": "APPROVED" in f.upper()}

# Build the 4-line loop router
def route(s: State):
    return END if s["approved"] or s["loops"] >= 3 else "coder"

# Compile State Machine
workflow = StateGraph(State)
workflow.add_node("coder", do_code)
workflow.add_node("reviewer", do_review)
workflow.set_entry_point("coder")
workflow.add_edge("coder", "reviewer")
workflow.add_conditional_edges("reviewer", route, {"coder": "coder", END: END})
app = workflow.compile()

