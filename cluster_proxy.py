import json
import http.server
import urllib.request

# =====================================================================
# OFFICIAL NATIVE OLLAMA ENDPOINTS & MODEL NAMES
# =====================================================================
DESKTOP_CODER_URL = "http://localhost:11434/v1/chat/completions"
DESKTOP_MODEL = "qwen2.5-coder:32b" # Native unconstrained Coder on desktop

LAPTOP_REVIEWER_URL = "http://192.168.2"
LAPTOP_MODEL = "qwen2.5:7b" # Native Reviewer on laptop (replaces qwen-reviewer-8k)

MAX_REWORK_LOOPS = 2

class DesktopOrchestratorHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        claude_request = json.loads(body.decode('utf-8'))
        
        user_prompt = claude_request["messages"][-1]["content"]
        print(f"\n🚀 [Proxy on Desktop] Task received from Claude Code: '{user_prompt[:50]}...'")
        
        current_code = ""
        review_feedback = "Initial implementation generation."
        loop_count = 0
        is_approved = False
        
        while not is_approved and loop_count <= MAX_REWORK_LOOPS:
            loop_count += 1
            print(f"\n🔄 [Loop {loop_count}/{MAX_REWORK_LOOPS + 1}]")
            
            # Step 1: Hit Local Desktop Coder
            print(f" └── [Local Coder ({DESKTOP_MODEL})] Generating code...")
            coder_payload = {
                "model": DESKTOP_MODEL,
                "messages": [
                    {"role": "system", "content": "You are an expert coder. Respond ONLY with valid executable code blocks. No conversation."},
                    {"role": "user", "content": f"Task: {user_prompt}\n\nPrevious Code Draft:\n{current_code}\n\nFeedback to fix:\n{review_feedback}"}
                ],
                "temperature": 0.2
            }
            
            try:
                coder_res = self.forward_request(DESKTOP_CODER_URL, coder_payload)
                current_code = json.loads(coder_res.decode('utf-8'))["choices"]["message"]["content"]
            except Exception as e:
                print(f" └── ❌ [Local Error] Failed to reach local desktop Coder: {e}")
                break
            
            # Step 2: Route code BACK to Laptop Reviewer over the bridge
            print(f" └── [Bridge -> Laptop Reviewer ({LAPTOP_MODEL})] Auditing implementation...")
            reviewer_payload = {
                "model": LAPTOP_MODEL,
                "messages": [
                    {"role": "system", "content": (
                        "You are a Senior Reviewer. Inspect the code against the task. "
                        "If it is correct, safe, and complete, reply with exactly the word: APPROVED. "
                        "If it has errors or missing requirements, output a concise bulleted list of bugs to fix."
                    )},
                    {"role": "user", "content": f"Original Task: {user_prompt}\n\nGenerated Code:\n{current_code}"}
                ],
                "temperature": 0.1
            }
            
            try:
                rev_res = self.forward_request(LAPTOP_REVIEWER_URL, reviewer_payload)
                review_feedback = json.loads(rev_res.decode('utf-8'))["choices"]["message"]["content"]
                
                if "APPROVED" in review_feedback.upper():
                    is_approved = True
                    print(" └── 🎉 [Reviewer Status] APPROVED!")
                else:
                    print(f" └── ⚠️ [Reviewer Status] Rework required. Notes: {review_feedback[:60]}...")
            except Exception as e:
                print(f" └── ❌ [Bridge Error] Failed to reach Laptop Reviewer: {e}")
                break

        # Package the final payload back for the Claude Code CLI client
        final_payload = {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "model": "claude-code-cluster",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": (
                        f"{current_code}\n\n"
                        f"```markdown\n"
                        f"■ Cluster Summary:\n"
                        f" - Iterations: {loop_count}\n"
                        f" - Review Node Status: {'Approved' if is_approved else 'Max Loops Reached'}\n"
                        f" - Laptop Audit Feedback: {review_feedback.replace('APPROVED', '').strip()}\n"
                        f"```"
                    )
                },
                "finish_reason": "stop"
            }]
        }
        
        response_data = json.dumps(final_payload).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_data)))
        self.end_headers()
        self.wfile.write(response_data)

    def forward_request(self, url, data):
        req = urllib.request.Request(
            url, data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            return response.read()

if __name__ == "__main__":
    server = http.server.HTTPServer(('0.0.0.0', 8000), DesktopOrchestratorHandler)
    print("🚀 Desktop Proxy Server listening on Port 8000...")
    server.serve_forever()

