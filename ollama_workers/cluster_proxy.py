import os
import sys
from typing import TypedDict
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

# =====================================================================
# 1. CORE GATEWAY ROUTING CONFIGURATION
# =====================================================================
LITELLM_GATEWAY_URL = "http://192.168.4.70:4000"
GATEWAY_KEY = "sk-d6305d8db9d21e97d64683cca4dd823ac0361302f98f4281a0ffba581ca4377c"

# Instantiate standardized models via LiteLLM abstraction
config = {"api_key": GATEWAY_KEY, "base_url": LITELLM_GATEWAY_URL}
coder = ChatOpenAI(model="cluster-coder", **config)
reviewer = ChatOpenAI(model="cluster-reviewer", **config)

# Explicit schema signature for state verification
class State(TypedDict):
    task: str
    code: str
    feedback: str
    loops: int
    approved: bool

# =====================================================================
# 2. STATE NODE INTERFACES
# =====================================================================
def do_code(s: State):
    """Executes code generation step."""
    print(f"\n[Loop {s['loops'] + 1}] 💻 Coder node is generating code...")
    p = ChatPromptTemplate.from_template("Task: {task}\nCode: {code}\nFix: {feedback}")
    return {"code": (p | coder).invoke(s).content, "loops": s["loops"] + 1}

def do_review(s: State):
    """Executes design review and validation step."""
    print("🔍 Reviewer node is auditing implementation...")
    f = (ChatPromptTemplate.from_template("Task: {task}\nReview: {code}") | reviewer).invoke(s).content
    print(f"📝 Reviewer Notes Summary: {f[:120].strip()}...")
    return {"feedback": f, "approved": "APPROVED" in f.upper()}

def route(s: State):
    """Conditional evaluation router function."""
    if s["approved"] or s["loops"] >= 3:
        print("\n🎉 Criteria satisfied or max turns hit! Terminating loop execution.")
        return END
    print("🔄 Quality standards not met. Routing back to Coder node.")
    return "coder"

# =====================================================================
# 3. PIPELINE MATRIX ARCHITECTURE
# =====================================================================
def build_workflow_graph():
    """Compiles individual processing steps into an execution mesh."""
    workflow = StateGraph(State)
    workflow.add_node("coder", do_code)
    workflow.add_node("reviewer", do_review)
    workflow.set_entry_point("coder")
    workflow.add_edge("coder", "reviewer")
    workflow.add_conditional_edges("reviewer", route, {"coder": "coder", END: END})
    return workflow.compile()

# =====================================================================
# 4. EXECUTION EXEC ENGINE
# =====================================================================
def main():
    """Main processing loop entry orchestrator."""
    print("🚀 Compiling multi-agent state graph pipeline...")
    app = build_workflow_graph()
    
    test_task = {
        "task": (
            "Write a robust Python script that safely rotates log files in a directory "
            "when they exceed 10MB, compressing old files into standard .gz targets."
        ),
        "code": "",
        "feedback": "Initial payload generation.",
        "loops": 0,
        "approved": False
    }
    
    try:
        print(f"📡 Dispatching task to cluster via link target: {LITELLM_GATEWAY_URL}")
        result = app.invoke(test_task)
        
        print("\n==================== WORKSPACE COMPILED OUTPUT ====================")
        print(result["code"])
        print("====================================================================")
        return 0
        
    except Exception as e:
        print(f"\n❌ Pipeline Aborted Due To Fatal Infrastructure Exception: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())

