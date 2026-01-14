"""Real-world WhatsApp Web browser agent test.

This test mimics how the actual Chrome extension client works:
1. Client captures initial screenshot
2. Client calls LangGraph agent with instruction + screenshot
3. Agent processes and returns tool calls
4. Client executes tools and resumes agent

Write your own assertions to verify agent behavior.

================================================================================
IMPORTANT: How LangGraph Interrupts Work (Lessons from Trace Analysis)
================================================================================

Based on actual LangSmith trace analysis (traces: 019bbd12-a5e2-78b0-958d-d954564b07f8,
019bbd12-96a8-7e70-aeb3-08bc11d045e1), here's how the interrupt/resume flow works:

1. **Screenshot Handling:**
   - Only ONE HumanMessage contains a screenshot (the initial user request)
   - After tool execution, NO screenshots are added to messages
   - Screenshots update STATE (`state.current_screenshot`), NOT messages
   - The model NEVER sees updated screenshots directly in messages

2. **Tool Execution Flow:**

   Server-side tools (load_skill, collect_data):
   - Execute immediately on server
   - Return ToolMessage with result
   - NO interrupt, NO screenshot capture
   - Message flow:
     AIMessage(tool_calls=['load_skill'])
     → ToolMessage("skill content")

   Client-side tools (wait, screenshot, click, type, etc.):
   - Create interrupt, pause graph execution
   - Client executes action and captures screenshot
   - Client resumes with Command(resume=BrowserToolResult)
   - tool_node updates state.current_screenshot
   - Only ToolMessage (text) added to messages
   - Message flow:
     AIMessage(tool_calls=['wait'])
     → ToolMessage("Waited 3000ms")  # NO screenshot here!

3. **How Model Sees Updated Screenshots:**
   - Initial screenshot: In first HumanMessage
   - Updated screenshots: Via state.current_screenshot
   - element_detection_node reads state.current_screenshot and detects UI elements
   - Detected elements injected into system prompt (as text coordinates)
   - **CRITICAL**: model_node injects state.current_screenshot as transient HumanMessage
   - Model sees BOTH: latest screenshot visually + element coordinates as text
   - This allows vision model (GPT-5-mini) to understand page state visually

4. **Graph Flow:**
   START → element_detection → model_node → tool_node → element_detection → ...
                                    ↓
                                   END

   After tool_node:
   - Updates state.current_screenshot (if tool captured screenshot)
   - Loops back to element_detection_node
   - element_detection uses new state.current_screenshot
   - model_node gets enriched prompt with detected elements

5. **Test Simulation Pattern:**

   ✅ CORRECT:
   ```python
   messages = [
       HumanMessage(content=[text, image_url]),  # Initial screenshot
       AIMessage(tool_calls=['wait']),
       ToolMessage("Waited 3000ms"),  # Text only, no screenshot
       AIMessage(tool_calls=['screenshot']),
       ToolMessage("Screenshot requested"),  # Text only, no screenshot
   ]
   state = AgentState(
       messages=messages,
       current_screenshot=new_screenshot,  # Updated here!
   )
   ```

   ❌ WRONG:
   ```python
   messages = [
       HumanMessage(content=[text, image_url]),
       AIMessage(tool_calls=['wait']),
       ToolMessage("Waited 3000ms"),
       HumanMessage(content=[image_url]),  # ❌ Don't add screenshots!
   ]
   ```

6. **Resume Payload Structure:**
   When client resumes after interrupt:
   ```python
   Command(resume={
       "result": "Waited 3000ms",  # Tool execution result
       "screenshot": "data:image/png;base64,...",  # Updated screenshot
       "viewport": {"width": 823, "height": 674}
   })
   ```

   This becomes the return value of `interrupt()` in tool_node.py:
   ```python
   result_dict: dict = interrupt(asdict(interrupt_payload))
   # screenshot goes to state.current_screenshot, NOT messages
   ```

   Then model_node.py injects state.current_screenshot as transient HumanMessage:
   ```python
   messages = list(state.messages)
   if state.current_screenshot:
       messages.append(HumanMessage(content=[{"type": "image_url", ...}]))
   response = model.invoke([system_message] + messages)
   # Screenshot is transient (not persisted to state.messages)
   ```

7. **Why This Matters for Tests:**
   - If you add extra HumanMessages with screenshots, you're testing a flow
     that never happens in production
   - The model's behavior will be different because it sees multiple screenshots
     in messages instead of relying on detected elements
   - Tests must match actual client behavior to catch real bugs

8. **Verification:**
   To verify this understanding, fetch actual traces using:
   ```bash
   cd servers/agents
   export LANGSMITH_API_KEY='...' && export LANGSMITH_PROJECT='anna-v3'
   uv run python scripts/fetch_trace.py --trace-id <trace_id>
   ```

   Then inspect the messages array to confirm:
   - Only first message has image_url
   - All subsequent messages are text-only (AIMessage, ToolMessage)
   - state.current_screenshot updates happen outside messages

================================================================================
"""

import base64
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# Load .env before importing model_node
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from agents.browser_agent.nodes.model_node import model_node
from agents.browser_agent.state import AgentState, Viewport


# Skip if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set - skipping integration tests"
)


# Path to test images
IMAGES_DIR = Path(__file__).parent / "images"


def load_image_as_data_url(image_path: Path) -> str:
    """Load an image file and convert to base64 data URL (mimics client screenshot capture)."""
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{image_data}"


class TestRealWorldWhatsAppFlow:
    """Test that mimics real Chrome extension + LangGraph flow."""

    @pytest.fixture
    def whatsapp_instruction(self) -> str:
        """The instruction sent from Chrome extension."""
        return "Collect messages from WhatsApp Web. Open the top 5 chats and collect messages."

    @pytest.fixture
    def initial_screenshot(self) -> str:
        """Initial screenshot captured by Chrome extension (you choose which image)."""
        # TODO: Change this to the image you want to test
        # ss-3.png = loaded WhatsApp with chat list
        # ss-2.png = loading screen with logo
        image_path = IMAGES_DIR / "ss-2.png"
        assert image_path.exists(), f"Test image not found: {image_path}"
        return load_image_as_data_url(image_path)

    def test_agent_load_skill(self, whatsapp_instruction: str, initial_screenshot: str):
        """
        Test the agent's FIRST response when it receives instruction + initial screenshot.

        This mimics what happens when the Chrome extension sends the first request.

        TODO: Write your assertions here based on what you expect the agent to do.
        """
        # Step 1: Client creates initial message (instruction + screenshot)
        human_message = HumanMessage(
            content=[
                {"type": "text", "text": whatsapp_instruction},
                {"type": "image_url", "image_url": {"url": initial_screenshot}},
            ]
        )

        # Step 2: Client creates initial state
        state = AgentState(
            messages=[human_message],
            current_screenshot=initial_screenshot,
            viewport=Viewport(width=1280, height=800),
            detected_elements=[],  # Client would populate this, but empty for now
        )

        # Step 3: Client calls agent
        result = model_node(state)

        # Step 4: Extract agent's response
        assert "messages" in result
        ai_message = result["messages"][0]
        assert isinstance(ai_message, AIMessage)

        # =================================================================
        # TODO: Write your assertions here!
        # =================================================================

        # Example assertions you might want:
        # - Check if agent called load_skill("whatsapp-web")
        # - Check if agent called wait() or click()
        # - Check what the agent said in its text response

        tool_names = [tc["name"] for tc in ai_message.tool_calls] if ai_message.tool_calls else []

        print("\n" + "="*70)
        print("AGENT RESPONSE:")
        print("="*70)
        print(f"Text: {ai_message.content}")
        print(f"Tools called: {tool_names}")
        if ai_message.tool_calls:
            for tc in ai_message.tool_calls:
                print(f"  - {tc['name']}({tc.get('args', {})})")
        print("="*70)

        # Assertion: Agent should call load_skill first when task mentions WhatsApp
        assert "load_skill" in tool_names, (
            f"Agent should call load_skill tool first when task mentions WhatsApp.\n"
            f"Instead called: {tool_names}"
        )

    def test_agent_decide_to_wait_when_loading(self, whatsapp_instruction: str, initial_screenshot: str):
        """
        Test that after loading WhatsApp skill, agent decides to wait when seeing loading screen.

        Flow:
        1. Agent receives instruction + loading screenshot
        2. Agent calls load_skill("whatsapp-web")
        3. Client executes load_skill (returns skill content)
        4. Agent sees loading screen again
        5. Agent should call wait() according to skill instructions
        """
        # Step 1: Simulate agent already called load_skill and got skill content back
        # NOTE: load_skill is a SERVER-SIDE tool, so:
        # - It executes immediately on the server
        # - Returns ToolMessage with skill content
        # - NO new screenshot is captured
        # - Agent continues with SAME screenshot

        # Load the actual skill content to simulate what the agent receives
        from pathlib import Path
        skill_path = Path(__file__).parent.parent.parent / "src" / "agents" / "browser_agent" / "prompts" / "skills" / "whatsapp-web.skill.prompt.md"
        with open(skill_path, "r") as f:
            skill_content = f.read()

        messages = [
            # Initial request
            HumanMessage(
                content=[
                    {"type": "text", "text": whatsapp_instruction},
                    {"type": "image_url", "image_url": {"url": initial_screenshot}},
                ]
            ),
            # Agent decided to load skill
            AIMessage(
                content="I will load the WhatsApp Web skill for specific instructions.",
                tool_calls=[{"id": "call_1", "name": "load_skill", "args": {"skill_name": "whatsapp-web"}}],
            ),
            # Server executed load_skill and returned skill content (NO SCREENSHOT)
            ToolMessage(
                content=skill_content,
                tool_call_id="call_1"
            ),
            # NO new screenshot here - agent continues with same screenshot
        ]

        # Step 2: Create state with this conversation history
        # NOTE: The skill content is already in the conversation context
        # through the ToolMessage above. No need for separate state tracking.
        state = AgentState(
            messages=messages,
            current_screenshot=initial_screenshot,
            viewport=Viewport(width=1280, height=800),
            detected_elements=[],
        )

        # Step 3: Call model_node to get agent's next decision
        result = model_node(state)

        # Step 4: Extract agent's response
        assert "messages" in result
        ai_message = result["messages"][0]
        assert isinstance(ai_message, AIMessage)

        tool_names = [tc["name"] for tc in ai_message.tool_calls] if ai_message.tool_calls else []

        print("\n" + "="*70)
        print("AGENT RESPONSE AFTER LOADING SKILL:")
        print("="*70)
        print(f"Text: {ai_message.content}")
        print(f"Tools called: {tool_names}")
        if ai_message.tool_calls:
            for tc in ai_message.tool_calls:
                print(f"  - {tc['name']}({tc.get('args', {})})")
        print("="*70)

        # Assertion: Agent should call wait when seeing loading screen (after skill is loaded)
        assert "wait" in tool_names, (
            f"Agent should call wait when seeing WhatsApp loading screen.\n"
            f"Instead called: {tool_names}\n"
            f"The screenshot shows a loading screen, so agent should wait."
        )

    def test_agent_decide_to_get_current_screenshot_by_calling_screenshot_tool(
        self,
        whatsapp_instruction: str,
        initial_screenshot: str
    ):
        """
        Test the full flow: load_skill → wait → screenshot → click first chat.

        IMPORTANT: Based on actual LangGraph trace analysis:
        - Only ONE HumanMessage with screenshot (the initial one)
        - After tool execution, only ToolMessages are added (NO screenshots)
        - Screenshots update STATE (state.current_screenshot), not messages
        - Model sees initial screenshot + text ToolMessages + detected elements

        Flow:
        1. Agent loads WhatsApp skill
        2. Agent sees loading screen, calls wait(3000)
        3. After wait, agent calls screenshot() to check state
        4. State gets updated with loaded screenshot (ss-3.png)
        5. Agent should click the first chat
        """
        # Load skill content
        from pathlib import Path
        skill_path = Path(__file__).parent.parent.parent / "src" / "agents" / "browser_agent" / "prompts" / "skills" / "whatsapp-web.skill.prompt.md"
        with open(skill_path, "r") as f:
            skill_content = f.read()

        # Load the loaded WhatsApp screenshot (ss-3.png)
        loaded_screenshot_path = IMAGES_DIR / "ss-3.png"
        assert loaded_screenshot_path.exists(), f"Test image not found: {loaded_screenshot_path}"
        loaded_screenshot = load_image_as_data_url(loaded_screenshot_path)

        # Build conversation history - ONLY ONE HumanMessage with screenshot
        messages = [
            # 1. Initial request with loading screenshot (ONLY screenshot in messages)
            HumanMessage(
                content=[
                    {"type": "text", "text": whatsapp_instruction},
                    {"type": "image_url", "image_url": {"url": initial_screenshot}},
                ]
            ),
            # 2. Agent loads skill (server-side, no interrupt)
            AIMessage(
                content="I will load the WhatsApp Web skill.",
                tool_calls=[{"id": "call_1", "name": "load_skill", "args": {"skill_name": "whatsapp-web"}}],
            ),
            ToolMessage(content=skill_content, tool_call_id="call_1"),
            # 3. Agent sees loading screen, decides to wait
            AIMessage(
                content="Page is loading, I will wait.",
                tool_calls=[{"id": "call_2", "name": "wait", "args": {"ms": 3000}}],
            ),
            # Tool result from wait - NO SCREENSHOT in messages
            ToolMessage(content="Waited 3000ms", tool_call_id="call_2"),
            # 4. Agent calls screenshot to check current state
            AIMessage(
                content="Let me check if page has loaded.",
                tool_calls=[{"id": "call_3", "name": "screenshot", "args": {"reason": "Check if page loaded"}}],
            ),
            # Tool result from screenshot - NO SCREENSHOT in messages, just text
            ToolMessage(content="Screenshot requested: Check if page loaded", tool_call_id="call_3"),
        ]

        # Create state with loaded screenshot in STATE (not in messages)
        # This simulates what happens after screenshot() tool executes:
        # - tool_node updates state.current_screenshot
        # - element_detection_node runs
        # - model_node sees updated state.current_screenshot via detected elements
        state = AgentState(
            messages=messages,
            current_screenshot=loaded_screenshot,  # Updated in STATE, not messages
            viewport=Viewport(width=1280, height=800),
            detected_elements=[],  # Would be populated by element_detection_node
        )

        # IMPORTANT: Run element_detection_node first to populate detected_elements
        # This is how the model "sees" the updated screenshot (via text descriptions)
        from agents.browser_agent.nodes.element_detection_node import element_detection_node

        print("\n" + "="*70)
        print("DEBUG: Running element_detection_node on loaded screenshot")
        print("="*70)

        detection_result = element_detection_node(state)
        state.detected_elements = detection_result.get("detected_elements", [])

        print(f"Detected {len(state.detected_elements)} elements:")
        for i, elem in enumerate(state.detected_elements[:10]):  # Print first 10
            print(f"  [{i+1}] {elem.element_type} '{elem.caption}' at grid ({elem.grid_center.x:.1f}, {elem.grid_center.y:.1f})")
        print("="*70)

        # Debug: What does the model actually see?
        print("\n" + "="*70)
        print("DEBUG: What the model will see")
        print("="*70)
        print(f"1. Messages in conversation: {len(messages)}")
        print(f"2. Last message type: {type(messages[-1]).__name__}")
        print(f"3. Last message content: {messages[-1].content[:100]}")
        print(f"4. Detected elements: {len(state.detected_elements)} elements (injected as text in system prompt)")
        print(f"5. Current screenshot in state: {'Yes' if state.current_screenshot else 'No'}")
        print(f"   NOTE: model_node will inject this screenshot as a transient HumanMessage for vision")
        print("="*70)

        # NOW call model_node - it should see detected elements as text
        result = model_node(state)

        # Extract agent's response
        assert "messages" in result
        ai_message = result["messages"][0]
        assert isinstance(ai_message, AIMessage)

        tool_names = [tc["name"] for tc in ai_message.tool_calls] if ai_message.tool_calls else []

        print("\n" + "="*70)
        print("AGENT RESPONSE AFTER SCREENSHOT UPDATED STATE:")
        print("="*70)
        print(f"Text: {ai_message.content}")
        print(f"Tools called: {tool_names}")
        if ai_message.tool_calls:
            for tc in ai_message.tool_calls:
                print(f"  - {tc['name']}({tc.get('args', {})})")
        print("="*70)

        # Assertion: Agent should click when state has loaded screenshot
        assert "click" in tool_names, (
            f"Agent should click the first chat when state.current_screenshot shows loaded WhatsApp.\n"
            f"Instead called: {tool_names}\n"
            f"The state.current_screenshot contains loaded WhatsApp with chat list visible."
        )

    def test_agent_decide_to_collect_data_after_opening_chat(
        self,
        whatsapp_instruction: str,
        initial_screenshot: str
    ):
       
        pass