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
        """The instruction sent from Chrome extension (matches database instruction)."""
        return """Collect the last 20 messages from each of the last 10 chats on WhatsApp Web.

Output Format (use collect_data tool):
- Format: 'WhatsApp Messages | ContactName → X messages (X/20): [Sender]: message (HH:MM) | ...'
- Identify sender: [User] for your messages (green bubbles), [ContactName] for received (white bubbles)

Example output:
'WhatsApp Messages | PAKE WA → 12 messages (12/20):
[PAKE WA]: Mau esuk ki Mas (05:47) |
[User]: Kok iso boso jowo sisan yo? (10:04) |
[PAKE WA]: Yo e (10:24)'

Workflow:
1. Load the whatsapp-web skill for site-specific guidance
2. For each chat:
   - Open the chat
   - Collect visible messages using collect_data (include count like "12/20")
   - If fewer than 20 messages, scroll up to load older ones
   - Collect newly visible messages
   - Continue until you have ~20 messages per chat
3. Move to the next chat and repeat

Remember: Call collect_data multiple times (once per chat or after each scroll). It does NOT end the task.
"""

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

    def test_agent_decide_to_click_first_chat(
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
        """
        Test that agent calls collect_data after opening a chat and seeing messages.

        Flow:
        1. Agent loaded skill
        2. Agent saw loading screen, called wait
        3. Agent called screenshot, saw chat list, called click
        4. NOW: Chat is open with messages visible (ss-4.png)
        5. Agent should call collect_data to collect visible messages
        """
        # Load skill content
        from pathlib import Path
        skill_path = Path(__file__).parent.parent.parent / "src" / "agents" / "browser_agent" / "prompts" / "skills" / "whatsapp-web.skill.prompt.md"
        with open(skill_path, "r") as f:
            skill_content = f.read()

        # Load the chat view screenshot (ss-4.png) - messages visible
        chat_view_screenshot_path = IMAGES_DIR / "ss-4.png"
        assert chat_view_screenshot_path.exists(), f"Test image not found: {chat_view_screenshot_path}"
        chat_view_screenshot = load_image_as_data_url(chat_view_screenshot_path)

        # Build conversation history - simulating the flow up to opening chat
        messages = [
            # 1. Initial request with loading screenshot
            HumanMessage(
                content=[
                    {"type": "text", "text": whatsapp_instruction},
                    {"type": "image_url", "image_url": {"url": initial_screenshot}},
                ]
            ),
            # 2. Agent loaded skill
            AIMessage(
                content="I will load the WhatsApp Web skill.",
                tool_calls=[{"id": "call_1", "name": "load_skill", "args": {"skill_name": "whatsapp-web"}}],
            ),
            ToolMessage(content=skill_content, tool_call_id="call_1"),
            # 3. Agent saw loading screen, called wait
            AIMessage(
                content="Page is loading, I will wait.",
                tool_calls=[{"id": "call_2", "name": "wait", "args": {"ms": 3000}}],
            ),
            ToolMessage(content="Waited 3000ms", tool_call_id="call_2"),
            # 4. Agent called screenshot to check state
            AIMessage(
                content="Let me check if page has loaded.",
                tool_calls=[{"id": "call_3", "name": "screenshot", "args": {"reason": "Check if page loaded"}}],
            ),
            ToolMessage(content="Screenshot requested: Check if page loaded", tool_call_id="call_3"),
            # 5. Agent saw chat list, clicked first chat
            AIMessage(
                content="I see the chat list. I will click the first chat.",
                tool_calls=[{"id": "call_4", "name": "click", "args": {"x": 10, "y": 30}}],
            ),
            ToolMessage(content="Clicked at grid position (10, 30)", tool_call_id="call_4"),
            # 6. Agent should wait briefly for chat to load
            AIMessage(
                content="Waiting for chat to load.",
                tool_calls=[{"id": "call_5", "name": "wait", "args": {"ms": 1000}}],
            ),
            ToolMessage(content="Waited 1000ms", tool_call_id="call_5"),
        ]

        # Create state with chat view screenshot (messages visible)
        state = AgentState(
            messages=messages,
            current_screenshot=chat_view_screenshot,  # ss-4.png with messages
            viewport=Viewport(width=1280, height=800),
            detected_elements=[],
        )

        # Run element detection on chat view
        from agents.browser_agent.nodes.element_detection_node import element_detection_node

        print("\n" + "="*70)
        print("DEBUG: Running element_detection_node on chat view screenshot")
        print("="*70)

        detection_result = element_detection_node(state)
        state.detected_elements = detection_result.get("detected_elements", [])

        print(f"Detected {len(state.detected_elements)} elements in chat view")
        for i, elem in enumerate(state.detected_elements[:10]):
            print(f"  [{i+1}] {elem.element_type} '{elem.caption}' at grid ({elem.grid_center.x:.1f}, {elem.grid_center.y:.1f})")
        print("="*70)

        # Call model_node to get agent's decision
        result = model_node(state)

        # Extract agent's response
        assert "messages" in result
        ai_message = result["messages"][0]
        assert isinstance(ai_message, AIMessage)

        tool_names = [tc["name"] for tc in ai_message.tool_calls] if ai_message.tool_calls else []

        print("\n" + "="*70)
        print("AGENT RESPONSE AFTER SEEING MESSAGES:")
        print("="*70)
        print(f"Text: {ai_message.content}")
        print(f"Tools called: {tool_names}")
        if ai_message.tool_calls:
            for tc in ai_message.tool_calls:
                print(f"  - {tc['name']}({tc.get('args', {})})")
        print("="*70)

        # Assertion: Agent should call collect_data when seeing messages in open chat
        assert "collect_data" in tool_names, (
            f"Agent should call collect_data when seeing messages in open chat.\n"
            f"Instead called: {tool_names}\n"
            f"The screenshot shows PAKE WA chat open with multiple messages visible."
        )

    def test_agent_decide_to_scroll_after_collecting(
        self,
        whatsapp_instruction: str,
        initial_screenshot: str
    ):
        """
        Test that agent scrolls up after collecting visible messages to load older messages.

        Flow:
        1. Agent loaded skill
        2. Agent saw loading screen, called wait
        3. Agent called screenshot, saw chat list, called click
        4. Chat opened, agent waited
        5. Agent collected visible messages with collect_data
        6. NOW: Agent should scroll up to load older messages
        """
        # Load skill content
        from pathlib import Path
        skill_path = Path(__file__).parent.parent.parent / "src" / "agents" / "browser_agent" / "prompts" / "skills" / "whatsapp-web.skill.prompt.md"
        with open(skill_path, "r") as f:
            skill_content = f.read()

        # Load the chat view screenshot (ss-4.png) - same as before, no new messages yet
        chat_view_screenshot_path = IMAGES_DIR / "ss-4.png"
        assert chat_view_screenshot_path.exists(), f"Test image not found: {chat_view_screenshot_path}"
        chat_view_screenshot = load_image_as_data_url(chat_view_screenshot_path)

        # Build conversation history including the collect_data call
        messages = [
            # 1. Initial request with loading screenshot
            HumanMessage(
                content=[
                    {"type": "text", "text": whatsapp_instruction},
                    {"type": "image_url", "image_url": {"url": initial_screenshot}},
                ]
            ),
            # 2. Agent loaded skill
            AIMessage(
                content="I will load the WhatsApp Web skill.",
                tool_calls=[{"id": "call_1", "name": "load_skill", "args": {"skill_name": "whatsapp-web"}}],
            ),
            ToolMessage(content=skill_content, tool_call_id="call_1"),
            # 3. Agent saw loading screen, called wait
            AIMessage(
                content="Page is loading, I will wait.",
                tool_calls=[{"id": "call_2", "name": "wait", "args": {"ms": 3000}}],
            ),
            ToolMessage(content="Waited 3000ms", tool_call_id="call_2"),
            # 4. Agent called screenshot to check state
            AIMessage(
                content="Let me check if page has loaded.",
                tool_calls=[{"id": "call_3", "name": "screenshot", "args": {"reason": "Check if page loaded"}}],
            ),
            ToolMessage(content="Screenshot requested: Check if page loaded", tool_call_id="call_3"),
            # 5. Agent saw chat list, clicked first chat
            AIMessage(
                content="I see the chat list. I will click the first chat.",
                tool_calls=[{"id": "call_4", "name": "click", "args": {"x": 10, "y": 30}}],
            ),
            ToolMessage(content="Clicked at grid position (10, 30)", tool_call_id="call_4"),
            # 6. Agent waited for chat to load
            AIMessage(
                content="Waiting for chat to load.",
                tool_calls=[{"id": "call_5", "name": "wait", "args": {"ms": 1000}}],
            ),
            ToolMessage(content="Waited 1000ms", tool_call_id="call_5"),
            # 7. Agent collected ALL visible messages (12 messages from ss-4.png)
            AIMessage(
                content="I see 12 messages visible in PAKE WA chat. I will collect them first.",
                tool_calls=[{
                    "id": "call_6",
                    "name": "collect_data",
                    "args": {
                        "data": [
                            "PAKE WA → 12 messages collected (12/20): "
                            "1. Mau esuk ki Mas (05:47); "
                            "2. Kok iso boso jowo sisan yo? (10:04); "
                            "3. Jajal upload en neng YouTube pak (10:04); "
                            "4. Kek ono gambar2 AI (10:04); "
                            "5. Ngerti kanggo sopo mas lagu kwi? (10:10); "
                            "6. sek lagi tak rungokne (10:11); "
                            "7. dinggo lek to kah? (10:12); "
                            "8. ref e marai nangis.. progressi chord e api pak (10:13); "
                            "9. wes tak rungokne sampek bar (10:14); "
                            "10. Yo e (10:24); "
                            "11. Makan di mana?? (12:45); "
                            "12. Neng warung mau pak (13:12)"
                        ]
                    }
                }],
            ),
            ToolMessage(content="Successfully collected 12 messages from PAKE WA (12/20 collected). Need 8 more messages to reach target.", tool_call_id="call_6"),
        ]

        # Create state with same chat view screenshot (no scroll happened yet)
        state = AgentState(
            messages=messages,
            current_screenshot=chat_view_screenshot,  # Same ss-4.png
            viewport=Viewport(width=1280, height=800),
            detected_elements=[],
        )

        # Run element detection
        from agents.browser_agent.nodes.element_detection_node import element_detection_node

        print("\n" + "="*70)
        print("DEBUG: State after collect_data")
        print("="*70)

        detection_result = element_detection_node(state)
        state.detected_elements = detection_result.get("detected_elements", [])

        print(f"Detected {len(state.detected_elements)} elements")
        print("="*70)

        # Call model_node to get agent's next decision
        result = model_node(state)

        # Extract agent's response
        assert "messages" in result
        ai_message = result["messages"][0]
        assert isinstance(ai_message, AIMessage)

        tool_names = [tc["name"] for tc in ai_message.tool_calls] if ai_message.tool_calls else []

        print("\n" + "="*70)
        print("AGENT RESPONSE AFTER COLLECTING:")
        print("="*70)
        print(f"Text: {ai_message.content}")
        print(f"Tools called: {tool_names}")
        if ai_message.tool_calls:
            for tc in ai_message.tool_calls:
                print(f"  - {tc['name']}({tc.get('args', {})})")
        print("="*70)

        # Accept two patterns:
        # Pattern 1: Direct scroll (ideal)
        # Pattern 2: Click to focus → then scroll (valid interaction pattern)

        if "scroll" in tool_names:
            # Pattern 1: Agent scrolls directly (ideal)
            print("\n✅ PASS: Agent scrolls directly to load older messages")

        elif "click" in tool_names:
            # Pattern 2: Agent clicks to focus first (valid pattern)
            print("\n📋 Agent clicked to focus message area (valid pattern)")
            print("   Now checking if agent scrolls in the next action...")

            # Simulate the click result - same screenshot since clicking doesn't change content
            messages.append(ai_message)
            click_tool_call = ai_message.tool_calls[0]
            messages.append(ToolMessage(
                content=f"Clicked at grid position ({click_tool_call['args']['x']}, {click_tool_call['args']['y']})",
                tool_call_id=click_tool_call["id"]
            ))

            # Update state with click result
            state.messages = messages

            # Run element detection again
            detection_result = element_detection_node(state)
            state.detected_elements = detection_result.get("detected_elements", [])

            # Get next decision
            result2 = model_node(state)
            ai_message2 = result2["messages"][0]
            tool_names2 = [tc["name"] for tc in ai_message2.tool_calls] if ai_message2.tool_calls else []

            print(f"\n   Next action: {tool_names2}")
            if ai_message2.tool_calls:
                for tc in ai_message2.tool_calls:
                    print(f"     - {tc['name']}({tc.get('args', {})})")

            # Now check if the agent scrolls
            assert "scroll" in tool_names2, (
                f"Agent clicked to focus (valid), but should scroll next to load older messages.\n"
                f"Instead called: {tool_names2}\n"
                f"Pattern should be: collect → click (to focus) → scroll → screenshot → collect more"
            )

            print("   ✅ PASS: Agent scrolls after clicking to focus")

        else:
            # Neither scroll nor click - unexpected
            assert False, (
                f"Agent should either scroll directly OR click to focus then scroll.\n"
                f"Instead called: {tool_names}\n"
                f"According to the instruction workflow: collect visible first, THEN scroll for more."
            )

    def test_agent_decide_to_collect_data_again_after_scroll(
        self,
        whatsapp_instruction: str,
        initial_screenshot: str
    ):
        """
        Test that agent collects data again after scrolling to see older messages.

        Flow:
        1. Agent loaded skill
        2. Agent saw loading screen, called wait
        3. Agent called screenshot, saw chat list, called click
        4. Chat opened, agent waited
        5. Agent collected visible messages (12/20)
        6. Agent scrolled up to load older messages
        7. Agent called screenshot to see newly loaded messages
        8. NOW: Agent should collect the newly visible messages
        """
        # Load skill content
        from pathlib import Path
        skill_path = Path(__file__).parent.parent.parent / "src" / "agents" / "browser_agent" / "prompts" / "skills" / "whatsapp-web.skill.prompt.md"
        with open(skill_path, "r") as f:
            skill_content = f.read()

        # Load the chat view screenshot AFTER scroll (ss-5.png) - now showing older messages
        scrolled_screenshot_path = IMAGES_DIR / "ss-5.png"
        assert scrolled_screenshot_path.exists(), f"Test image not found: {scrolled_screenshot_path}"
        scrolled_screenshot = load_image_as_data_url(scrolled_screenshot_path)

        # Build conversation history including the scroll action
        messages = [
            # 1. Initial request with loading screenshot
            HumanMessage(
                content=[
                    {"type": "text", "text": whatsapp_instruction},
                    {"type": "image_url", "image_url": {"url": initial_screenshot}},
                ]
            ),
            # 2. Agent loaded skill
            AIMessage(
                content="I will load the WhatsApp Web skill.",
                tool_calls=[{"id": "call_1", "name": "load_skill", "args": {"skill_name": "whatsapp-web"}}],
            ),
            ToolMessage(content=skill_content, tool_call_id="call_1"),
            # 3. Agent saw loading screen, called wait
            AIMessage(
                content="Page is loading, I will wait.",
                tool_calls=[{"id": "call_2", "name": "wait", "args": {"ms": 3000}}],
            ),
            ToolMessage(content="Waited 3000ms", tool_call_id="call_2"),
            # 4. Agent called screenshot to check state
            AIMessage(
                content="Let me check if page has loaded.",
                tool_calls=[{"id": "call_3", "name": "screenshot", "args": {"reason": "Check if page loaded"}}],
            ),
            ToolMessage(content="Screenshot requested: Check if page loaded", tool_call_id="call_3"),
            # 5. Agent saw chat list, clicked first chat
            AIMessage(
                content="I see the chat list. I will click the first chat.",
                tool_calls=[{"id": "call_4", "name": "click", "args": {"x": 10, "y": 30}}],
            ),
            ToolMessage(content="Clicked at grid position (10, 30)", tool_call_id="call_4"),
            # 6. Agent waited for chat to load
            AIMessage(
                content="Waiting for chat to load.",
                tool_calls=[{"id": "call_5", "name": "wait", "args": {"ms": 1000}}],
            ),
            ToolMessage(content="Waited 1000ms", tool_call_id="call_5"),
            # 7. Agent collected visible messages (12/20)
            AIMessage(
                content="I see 12 messages visible in PAKE WA chat. I will collect them first.",
                tool_calls=[{
                    "id": "call_6",
                    "name": "collect_data",
                    "args": {
                        "data": [
                            "WhatsApp Messages | PAKE WA → 12 messages (12/20):\n"
                            "[User]: Mau esuk ki Mas (05:47) | "
                            "[PAKE WA]: Kok iso boso jowo sisan yo? (10:04) | "
                            "[User]: Jajal upload en neng YouTube pak (10:04) | "
                            "[User]: Kek ono gambar2 AI (10:04) | "
                            "[PAKE WA]: Ngerti kanggo sopo mas lagu kwi? (10:10) | "
                            "[User]: sek lagi tak rungokne (10:11) | "
                            "[PAKE WA]: dinggo lek to kah? (10:12) | "
                            "[User]: ref e marai nangis.. progressi chord e api pak (10:13) | "
                            "[User]: wes tak rungokne sampek bar (10:14) | "
                            "[PAKE WA]: Yo e (10:24) | "
                            "[User]: Makan di mana?? (12:45) | "
                            "[PAKE WA]: Neng warung mau pak (13:12)"
                        ]
                    }
                }],
            ),
            ToolMessage(content="Successfully collected 12 messages from PAKE WA (12/20 collected). Need 8 more messages to reach target.", tool_call_id="call_6"),
            # 8. Agent scrolled up to load older messages
            AIMessage(
                content="I need 8 more messages. I will scroll up to load older messages.",
                tool_calls=[{"id": "call_7", "name": "scroll", "args": {"direction": "up", "amount": 300}}],
            ),
            ToolMessage(content="Scrolled up by 300 pixels", tool_call_id="call_7"),
            # 9. Agent called screenshot to see newly loaded messages
            AIMessage(
                content="Let me take a screenshot to see the newly loaded messages after scrolling.",
                tool_calls=[{"id": "call_8", "name": "screenshot", "args": {"reason": "See messages after scroll"}}],
            ),
            ToolMessage(content="Screenshot requested: See messages after scroll", tool_call_id="call_8"),
        ]

        # Create state with scrolled screenshot (ss-5.png showing more messages)
        state = AgentState(
            messages=messages,
            current_screenshot=scrolled_screenshot,  # NOW showing ss-5.png with older messages
            viewport=Viewport(width=1280, height=800),
            detected_elements=[],
        )

        # Run element detection
        from agents.browser_agent.nodes.element_detection_node import element_detection_node

        print("\n" + "="*70)
        print("DEBUG: State after scroll")
        print("="*70)

        detection_result = element_detection_node(state)
        state.detected_elements = detection_result.get("detected_elements", [])

        print(f"Detected {len(state.detected_elements)} elements")
        print("="*70)

        # Call model_node to get agent's next decision
        result = model_node(state)

        # Extract agent's response
        assert "messages" in result
        ai_message = result["messages"][0]
        assert isinstance(ai_message, AIMessage)

        tool_names = [tc["name"] for tc in ai_message.tool_calls] if ai_message.tool_calls else []

        print("\n" + "="*70)
        print("AGENT RESPONSE AFTER SCROLL:")
        print("="*70)
        print(f"Text: {ai_message.content}")
        print(f"Tools called: {tool_names}")
        if ai_message.tool_calls:
            for tc in ai_message.tool_calls:
                print(f"  - {tc['name']}({tc.get('args', {})})")
        print("="*70)

        # Assertion: Agent should collect the newly visible messages
        assert "collect_data" in tool_names, (
            f"Agent should collect newly visible messages after scrolling.\n"
            f"Instead called: {tool_names}\n"
            f"After scrolling, more older messages are now visible and should be collected."
        )

    def test_agent_decide_to_click_next_chat_after_collecting(
        self,
        whatsapp_instruction: str,
        initial_screenshot: str
    ):
        """
        Test that agent clicks next chat after finishing data collection from current chat.

        Flow:
        1. Agent loaded skill
        2. Agent saw loading screen, called wait
        3. Agent called screenshot, saw chat list, called click
        4. Chat opened, agent waited
        5. Agent collected visible messages (12/20)
        6. Agent scrolled up to load older messages
        7. Agent called screenshot to see newly loaded messages
        8. Agent collected newly visible messages (reaching 20/20 total)
        9. NOW: Agent should click the next chat to continue collection
        """
        # Load skill content
        from pathlib import Path
        skill_path = Path(__file__).parent.parent.parent / "src" / "agents" / "browser_agent" / "prompts" / "skills" / "whatsapp-web.skill.prompt.md"
        with open(skill_path, "r") as f:
            skill_content = f.read()

        # Still using ss-5.png - same screen, but agent has now collected all messages
        scrolled_screenshot_path = IMAGES_DIR / "ss-5.png"
        assert scrolled_screenshot_path.exists(), f"Test image not found: {scrolled_screenshot_path}"
        scrolled_screenshot = load_image_as_data_url(scrolled_screenshot_path)

        # Build conversation history including the second collect_data
        messages = [
            # 1. Initial request with loading screenshot
            HumanMessage(
                content=[
                    {"type": "text", "text": whatsapp_instruction},
                    {"type": "image_url", "image_url": {"url": initial_screenshot}},
                ]
            ),
            # 2. Agent loaded skill
            AIMessage(
                content="I will load the WhatsApp Web skill.",
                tool_calls=[{"id": "call_1", "name": "load_skill", "args": {"skill_name": "whatsapp-web"}}],
            ),
            ToolMessage(content=skill_content, tool_call_id="call_1"),
            # 3. Agent saw loading screen, called wait
            AIMessage(
                content="Page is loading, I will wait.",
                tool_calls=[{"id": "call_2", "name": "wait", "args": {"ms": 3000}}],
            ),
            ToolMessage(content="Waited 3000ms", tool_call_id="call_2"),
            # 4. Agent called screenshot to check state
            AIMessage(
                content="Let me check if page has loaded.",
                tool_calls=[{"id": "call_3", "name": "screenshot", "args": {"reason": "Check if page loaded"}}],
            ),
            ToolMessage(content="Screenshot requested: Check if page loaded", tool_call_id="call_3"),
            # 5. Agent saw chat list, clicked first chat (PAKE WA)
            AIMessage(
                content="I see the chat list. I will click the first chat.",
                tool_calls=[{"id": "call_4", "name": "click", "args": {"x": 10, "y": 30}}],
            ),
            ToolMessage(content="Clicked at grid position (10, 30)", tool_call_id="call_4"),
            # 6. Agent waited for chat to load
            AIMessage(
                content="Waiting for chat to load.",
                tool_calls=[{"id": "call_5", "name": "wait", "args": {"ms": 1000}}],
            ),
            ToolMessage(content="Waited 1000ms", tool_call_id="call_5"),
            # 7. Agent collected first batch of visible messages (12/20)
            AIMessage(
                content="I see 12 messages visible in PAKE WA chat. I will collect them first.",
                tool_calls=[{
                    "id": "call_6",
                    "name": "collect_data",
                    "args": {
                        "data": [
                            "WhatsApp Messages | PAKE WA → 12 messages (12/20):\n"
                            "[User]: Mau esuk ki Mas (05:47) | "
                            "[PAKE WA]: Kok iso boso jowo sisan yo? (10:04) | "
                            "[User]: Jajal upload en neng YouTube pak (10:04) | "
                            "[User]: Kek ono gambar2 AI (10:04) | "
                            "[PAKE WA]: Ngerti kanggo sopo mas lagu kwi? (10:10) | "
                            "[User]: sek lagi tak rungokne (10:11) | "
                            "[PAKE WA]: dinggo lek to kah? (10:12) | "
                            "[User]: ref e marai nangis.. progressi chord e api pak (10:13) | "
                            "[User]: wes tak rungokne sampek bar (10:14) | "
                            "[PAKE WA]: Yo e (10:24) | "
                            "[User]: Makan di mana?? (12:45) | "
                            "[PAKE WA]: Neng warung mau pak (13:12)"
                        ]
                    }
                }],
            ),
            ToolMessage(content="Successfully collected 12 messages from PAKE WA (12/20 collected). Need 8 more messages to reach target.", tool_call_id="call_6"),
            # 8. Agent scrolled up to load older messages
            AIMessage(
                content="I need 8 more messages. I will scroll up to load older messages.",
                tool_calls=[{"id": "call_7", "name": "scroll", "args": {"direction": "up", "amount": 300}}],
            ),
            ToolMessage(content="Scrolled up by 300 pixels", tool_call_id="call_7"),
            # 9. Agent called screenshot to see newly loaded messages
            AIMessage(
                content="Let me take a screenshot to see the newly loaded messages after scrolling.",
                tool_calls=[{"id": "call_8", "name": "screenshot", "args": {"reason": "See messages after scroll"}}],
            ),
            ToolMessage(content="Screenshot requested: See messages after scroll", tool_call_id="call_8"),
            # 10. Agent collected newly visible older messages (reaching 20/20 total)
            AIMessage(
                content="I see more messages after scrolling. I will collect them to reach 20 messages total.",
                tool_calls=[{
                    "id": "call_9",
                    "name": "collect_data",
                    "args": {
                        "data": [
                            "WhatsApp Messages | PAKE WA → 20 messages (20/20):\n"
                            "[PAKE WA]: Lak io loro opo pak? (14:51) | "
                            "[User]: Ginjal e mas (14:51) | "
                            "[PAKE WA]: Ginjal e nyopo pak? (14:52) | "
                            "[User]: Disfungsi mas (14:56) | "
                            "[User]: tapi si jk mungkin hasil e bersik (15:07) | "
                            "[System]: Voice call (21:11) | "
                            "[User]: Audio message (10:02) | "
                            "[User]: Jam 5.47 | "
                            "[User]: Mau esuk ki Mas (05:47) | "
                            "[PAKE WA]: Kok iso boso jowo sisan yo? (10:04) | "
                            "[User]: Jajal upload en neng YouTube pak (10:04) | "
                            "[User]: Kek ono gambar2 AI (10:04) | "
                            "[PAKE WA]: Ngerti kanggo sopo mas lagu kwi? (10:10) | "
                            "[User]: sek lagi tak rungokne (10:11) | "
                            "[PAKE WA]: dinggo lek to kah? (10:12) | "
                            "[User]: ref e marai nangis.. progressi chord e api pak (10:13) | "
                            "[User]: wes tak rungokne sampek bar (10:14) | "
                            "[PAKE WA]: Yo e (10:24) | "
                            "[User]: Makan di mana?? (12:45) | "
                            "[PAKE WA]: Neng warung mau pak (13:12)"
                        ]
                    }
                }],
            ),
            ToolMessage(content="Successfully collected 20 messages from PAKE WA (20/20 collected). Completed collection for this chat. Task requires collecting from 10 chats total - need to move to next chat.", tool_call_id="call_9"),
        ]

        # Create state with same screenshot (agent needs to navigate back to chat list)
        state = AgentState(
            messages=messages,
            current_screenshot=scrolled_screenshot,  # Still in PAKE WA chat, can see chat list on left
            viewport=Viewport(width=1280, height=800),
            detected_elements=[],
        )

        # Run element detection
        from agents.browser_agent.nodes.element_detection_node import element_detection_node

        print("\n" + "="*70)
        print("DEBUG: State after collecting 20/20 messages")
        print("="*70)

        detection_result = element_detection_node(state)
        state.detected_elements = detection_result.get("detected_elements", [])

        print(f"Detected {len(state.detected_elements)} elements")
        print("="*70)

        # Call model_node to get agent's next decision
        result = model_node(state)

        # Extract agent's response
        assert "messages" in result
        ai_message = result["messages"][0]
        assert isinstance(ai_message, AIMessage)

        tool_names = [tc["name"] for tc in ai_message.tool_calls] if ai_message.tool_calls else []

        print("\n" + "="*70)
        print("AGENT RESPONSE AFTER COMPLETING CHAT COLLECTION:")
        print("="*70)
        print(f"Text: {ai_message.content}")
        print(f"Tools called: {tool_names}")
        if ai_message.tool_calls:
            for tc in ai_message.tool_calls:
                print(f"  - {tc['name']}({tc.get('args', {})})")
        print("="*70)

        # Assertion: Agent should click the next chat to continue collection
        assert "click" in tool_names, (
            f"Agent should click the next chat after finishing collection from current chat.\n"
            f"Instead called: {tool_names}\n"
            f"Collected 20/20 messages from PAKE WA. Task requires 10 chats total - need to move to next chat."
        )

    def test_agent_click_reasoning_with_green_banner(
        self,
        whatsapp_instruction: str,
        initial_screenshot: str
    ):
        """
        DIAGNOSTIC TEST: Understand why agent clicks green banner instead of first chat.

        This test does NOT aim to pass. Instead, it captures the AI's reasoning
        to help us understand:
        - What coordinates the AI chooses
        - Why the AI picks those coordinates
        - What visual cues mislead the AI

        ss-6.png shows:
        - Green "Turn on background sync" banner at top
        - Chat list below (My family, AHMAD SOMPRET FAMILY, PAKE WA, etc.)

        Observed behavior from logs:
        - AI clicks progressively higher: y=38 → y=30 → y=28
        - Gets stuck clicking green banner text instead of chat items
        """
        # Load skill content
        from pathlib import Path
        skill_path = Path(__file__).parent.parent.parent / "src" / "agents" / "browser_agent" / "prompts" / "skills" / "whatsapp-web.skill.prompt.md"
        with open(skill_path, "r") as f:
            skill_content = f.read()

        # Load ss-6.png showing chat list with green banner
        screenshot_path = IMAGES_DIR / "ss-6.png"
        assert screenshot_path.exists(), f"Test image not found: {screenshot_path}"
        screenshot = load_image_as_data_url(screenshot_path)

        # Build conversation history - agent just finished waiting and should click first chat
        messages = [
            # 1. Initial request with loading screenshot
            HumanMessage(
                content=[
                    {"type": "text", "text": whatsapp_instruction},
                    {"type": "image_url", "image_url": {"url": initial_screenshot}},
                ]
            ),
            # 2. Agent loaded skill
            AIMessage(
                content="I will load the WhatsApp Web skill.",
                tool_calls=[{"id": "call_1", "name": "load_skill", "args": {"skill_name": "whatsapp-web"}}],
            ),
            ToolMessage(content=skill_content, tool_call_id="call_1"),
            # 3. Agent saw loading screen, called wait
            AIMessage(
                content="Page is loading, I will wait.",
                tool_calls=[{"id": "call_2", "name": "wait", "args": {"ms": 3000}}],
            ),
            ToolMessage(content="Waited 3000ms", tool_call_id="call_2"),
            # 4. NOW: Agent should click first chat, but ss-6.png has green banner
        ]

        # Create state with ss-6.png (chat list with green banner)
        state = AgentState(
            messages=messages,
            current_screenshot=screenshot,
            viewport=Viewport(width=1280, height=800),
            detected_elements=[],
        )

        # Run element detection
        from agents.browser_agent.nodes.element_detection_node import element_detection_node

        print("\n" + "="*80)
        print("DIAGNOSTIC TEST: Why does AI click green banner instead of first chat?")
        print("="*80)
        print("Screenshot: ss-6.png")
        print("Contains: Green 'Turn on background sync' banner + chat list below")
        print("="*80)

        detection_result = element_detection_node(state)
        state.detected_elements = detection_result.get("detected_elements", [])

        print(f"\nDetected {len(state.detected_elements)} UI elements:")
        for i, elem in enumerate(state.detected_elements[:20]):  # Show first 20
            print(f"  [{i+1}] {elem.element_type}: '{elem.caption}' at grid ({elem.grid_center.x}, {elem.grid_center.y})")
        if len(state.detected_elements) > 20:
            print(f"  ... and {len(state.detected_elements) - 20} more elements")
        print("="*80)

        # Call model_node to get agent's decision
        result = model_node(state)

        # Extract agent's response
        assert "messages" in result
        ai_message = result["messages"][0]
        assert isinstance(ai_message, AIMessage)

        # Print AI's reasoning
        print("\n" + "="*80)
        print("AI'S REASONING:")
        print("="*80)
        print(f"Thought process: {ai_message.content}")
        print("="*80)

        # Print tool calls
        if ai_message.tool_calls:
            print("\nTOOL CALLS:")
            print("="*80)
            for tc in ai_message.tool_calls:
                print(f"Tool: {tc['name']}")
                print(f"Args: {tc.get('args', {})}")
                if tc['name'] == 'click':
                    x = tc['args'].get('x')
                    y = tc['args'].get('y')
                    print(f"Grid coordinates: ({x}, {y})")
                    # Convert to pixel coordinates for reference
                    pixel_x = int((x / 100) * state.viewport.width)
                    pixel_y = int((y / 100) * state.viewport.height)
                    print(f"Pixel coordinates: ({pixel_x}, {pixel_y})")
                    print(f"\nANALYSIS:")
                    if y < 20:
                        print(f"  ⚠️  Y coordinate {y} is VERY HIGH (top 20% of screen)")
                        print(f"  This likely hits the green banner, not the chat list!")
                    elif y < 35:
                        print(f"  ⚠️  Y coordinate {y} is HIGH (top 35% of screen)")
                        print(f"  May hit green banner or area close to it")
                    else:
                        print(f"  ✓ Y coordinate {y} seems reasonable for chat list")
                print("-" * 80)
            print("="*80)
        else:
            print("\nNo tool calls made (agent may have finished or encountered error)")

        # Print conclusion
        print("\n" + "="*80)
        print("DIAGNOSTIC CONCLUSION:")
        print("="*80)
        print("This test captures the AI's decision-making process.")
        print("Review the reasoning above to understand:")
        print("1. What visual cues the AI focuses on")
        print("2. Why it chooses specific coordinates")
        print("3. What misleads it to click the banner instead of chat items")
        print("="*80)

        # Intentionally NO assertion - we want to see the failure mode
        # The test "passes" by documenting the problem, not by being correct

    def test_agent_stuck_clicking_banner_after_failed_attempt(
        self,
        whatsapp_instruction: str,
        initial_screenshot: str
    ):
        """
        DIAGNOSTIC TEST: Why does AI keep clicking banner after first failed attempt?

        This simulates the ACTUAL failure scenario from logs:
        1. AI clicks at (20, 38) - hits green banner
        2. Screenshot shows SAME chat list (not opened)
        3. AI tries again at (20, 30) - STILL hits banner
        4. AI tries again at (18, 28) - STUCK in loop

        The question: Why does AI move UPWARD (toward banner) instead of DOWNWARD (toward chats)?
        """
        # Load skill content
        from pathlib import Path
        skill_path = Path(__file__).parent.parent.parent / "src" / "agents" / "browser_agent" / "prompts" / "skills" / "whatsapp-web.skill.prompt.md"
        with open(skill_path, "r") as f:
            skill_content = f.read()

        # Load ss-6.png showing chat list with green banner
        screenshot_path = IMAGES_DIR / "ss-6.png"
        assert screenshot_path.exists(), f"Test image not found: {screenshot_path}"
        screenshot = load_image_as_data_url(screenshot_path)

        # Build conversation history - AI already clicked once, but it failed
        messages = [
            # 1. Initial request
            HumanMessage(
                content=[
                    {"type": "text", "text": whatsapp_instruction},
                    {"type": "image_url", "image_url": {"url": initial_screenshot}},
                ]
            ),
            # 2. Agent loaded skill
            AIMessage(
                content="I will load the WhatsApp Web skill.",
                tool_calls=[{"id": "call_1", "name": "load_skill", "args": {"skill_name": "whatsapp-web"}}],
            ),
            ToolMessage(content=skill_content, tool_call_id="call_1"),
            # 3. Agent saw loading, waited
            AIMessage(
                content="Page is loading, I will wait.",
                tool_calls=[{"id": "call_2", "name": "wait", "args": {"ms": 3000}}],
            ),
            ToolMessage(content="Waited 3000ms", tool_call_id="call_2"),
            # 4. First click attempt at y=38 (from logs)
            AIMessage(
                content="I see the chat list. I will click the first chat.",
                tool_calls=[{"id": "call_3", "name": "click", "args": {"x": 20, "y": 38}}],
            ),
            # THIS IS THE KEY: Click hit green banner, not chat
            ToolMessage(
                content='Clicked on span.x78zum5.x1c4vz4f.x2lah0s.xdl72j9.xdt5ytf "ic-closeic-syncTurn on backgro" at (212, 256)',
                tool_call_id="call_3"
            ),
            # 5. NOW: Screenshot still shows chat list (chat didn't open)
            #     What will AI do next? Move up or down?
        ]

        # State AFTER first failed click - still showing ss-6.png
        state = AgentState(
            messages=messages,
            current_screenshot=screenshot,
            viewport=Viewport(width=1280, height=800),
            detected_elements=[],
        )

        # Run element detection
        from agents.browser_agent.nodes.element_detection_node import element_detection_node

        print("\n" + "="*80)
        print("DIAGNOSTIC TEST: Why does AI move UPWARD after failed click?")
        print("="*80)
        print("Scenario: AI clicked at y=38, hit green banner, chat didn't open")
        print("Screenshot: Still shows ss-6.png (same chat list with banner)")
        print("Question: Will AI try higher coordinates (banner) or lower (actual chats)?")
        print("="*80)

        detection_result = element_detection_node(state)
        state.detected_elements = detection_result.get("detected_elements", [])

        print(f"\nDetected {len(state.detected_elements)} UI elements")
        print("="*80)

        # Call model_node to get agent's next decision
        result = model_node(state)

        # Extract agent's response
        assert "messages" in result
        ai_message = result["messages"][0]
        assert isinstance(ai_message, AIMessage)

        # Print AI's reasoning
        print("\n" + "="*80)
        print("AI'S REASONING AFTER FAILED CLICK:")
        print("="*80)
        print(f"Previous action: Clicked at (20, 38) but hit green banner")
        print(f"Current thought: {ai_message.content}")
        print("="*80)

        # Print tool calls
        if ai_message.tool_calls:
            print("\nNEXT ACTION:")
            print("="*80)
            for tc in ai_message.tool_calls:
                print(f"Tool: {tc['name']}")
                if tc['name'] == 'click':
                    x = tc['args'].get('x')
                    y = tc['args'].get('y')
                    prev_y = 38

                    print(f"Previous click: y={prev_y}")
                    print(f"New click: y={y}")
                    print(f"Grid coordinates: ({x}, {y})")

                    pixel_x = int((x / 100) * state.viewport.width)
                    pixel_y = int((y / 100) * state.viewport.height)
                    print(f"Pixel coordinates: ({pixel_x}, {pixel_y})")

                    print(f"\n🔍 MOVEMENT ANALYSIS:")
                    if y < prev_y:
                        diff = prev_y - y
                        print(f"  ⬆️  MOVED UP by {diff} grid units (from y={prev_y} to y={y})")
                        print(f"  ⚠️  Moving TOWARD green banner (wrong direction!)")
                        print(f"  💡 Why? The AI may think it needs to click 'above' the banner")
                        print(f"      to access the chat, but it's actually clicking IN the banner!")
                    elif y > prev_y:
                        diff = y - prev_y
                        print(f"  ⬇️  MOVED DOWN by {diff} grid units (from y={prev_y} to y={y})")
                        print(f"  ✅ Moving AWAY from banner (correct direction!)")
                        print(f"  💡 The AI recognized it needs to go lower to hit actual chats")
                    else:
                        print(f"  ↔️  SAME Y coordinate - trying different X position")

                    print(f"\n📍 COORDINATE ASSESSMENT:")
                    if y < 25:
                        print(f"  🚨 Y={y} is in TOP 25% - DEFINITELY green banner area")
                    elif y < 35:
                        print(f"  ⚠️  Y={y} is in TOP 35% - Likely banner or very close to it")
                    else:
                        print(f"  ✓ Y={y} is below 35% - Should be in chat list area")
                else:
                    print(f"Args: {tc.get('args', {})}")
                print("-" * 80)
            print("="*80)

        # Print conclusion
        print("\n" + "="*80)
        print("KEY INSIGHTS:")
        print("="*80)
        print("This test reveals WHY the AI gets stuck in a loop:")
        print("1. What direction does the AI move after failed click?")
        print("2. What reasoning does it provide for this movement?")
        print("3. Does it recognize the banner as an obstacle?")
        print("4. How can we guide it to avoid the banner area?")
        print("="*80)

    def test_agent_must_decide_to_scroll_after_clicking_first_chat(
        self,
        whatsapp_instruction: str,
        initial_screenshot: str
    ):
        pass

    def test_agent_scrolls_message_area_with_coordinates(
        self, whatsapp_instruction: str, initial_screenshot: str
    ):
        """Test that agent scrolls with coordinates after collecting visible messages.

        This test verifies the NEW targeted scrolling feature where the agent
        can specify x,y coordinates to scroll a specific scrollable area.

        Realistic flow:
        1. Agent sees chat open with 12 visible messages
        2. Agent collects those 12 messages first (12/20)
        3. Agent realizes it needs 8 more messages
        4. Agent scrolls UP in message area with coordinates to load older messages
        """
        # Load skill content
        from pathlib import Path
        skill_path = Path(__file__).parent.parent.parent / "src" / "agents" / "browser_agent" / "prompts" / "skills" / "whatsapp-web.skill.prompt.md"
        with open(skill_path, "r") as f:
            skill_content = f.read()

        # Load chat view screenshot (ss-4.png) - shows 12 messages
        chat_view_screenshot_path = IMAGES_DIR / "ss-4.png"
        assert chat_view_screenshot_path.exists(), f"Test image not found: {chat_view_screenshot_path}"
        chat_view_screenshot = load_image_as_data_url(chat_view_screenshot_path)

        # Build conversation: agent has loaded skill, opened chat, and JUST collected 12 messages
        messages = [
            HumanMessage(
                content=[
                    {"type": "text", "text": whatsapp_instruction},
                    {"type": "image_url", "image_url": {"url": initial_screenshot}},
                ]
            ),
            AIMessage(
                content="Loading WhatsApp skill.",
                tool_calls=[{"id": "call_1", "name": "load_skill", "args": {"skill_name": "whatsapp-web"}}],
            ),
            ToolMessage(content=skill_content, tool_call_id="call_1"),
            # Agent collected the visible 12 messages from ss-4.png
            AIMessage(
                content="I see PAKE WA chat with 12 visible messages. Collecting them.",
                tool_calls=[{
                    "id": "call_2",
                    "name": "collect_data",
                    "args": {
                        "data": [
                            "WhatsApp Messages | PAKE WA → 12 messages (12/20): "
                            "[PAKE WA]: Mau esuk ki Mas (05:47) | "
                            "[User]: Kok iso boso jowo sisan yo? (10:04) | "
                            "[User]: Jajal upload en neng YouTube pak (10:04) | "
                            "[User]: Kek ono gambar2 AI (10:04) | "
                            "[PAKE WA]: Ngerti kanggo sopo mas lagu kwi? (10:10) | "
                            "[User]: sek lagi tak rungokne (10:11) | "
                            "[User]: dinggo lek to kah? (10:12) | "
                            "[User]: ref e marai nangis.. progressi chord e api pak (10:13) | "
                            "[User]: wes tak rungokne sampek bar (10:14) | "
                            "[PAKE WA]: Yo e (10:24) | "
                            "[PAKE WA]: Makan di mana?? (12:45) | "
                            "[User]: Neng warung mau pak (13:12)"
                        ]
                    }
                }],
            ),
            ToolMessage(content="Collected 12 messages successfully (12/20). Need 8 more to reach 20.", tool_call_id="call_2"),
        ]

        # Create state - same screenshot (no scroll happened yet)
        state = AgentState(
            messages=messages,
            current_screenshot=chat_view_screenshot,  # Same ss-4.png
            viewport=Viewport(width=1280, height=800),
            detected_elements=[],
        )

        print("\n" + "=" * 80)
        print("TESTING: Scroll with Coordinates After Collecting")
        print("=" * 80)
        print("Setup: Chat open, already collected 12/20 messages")
        print("Expected: Agent scrolls UP with coordinates to load 8 more messages")
        print("Target: Message area (X=60, Y=50)")
        print("=" * 80)

        # Run element detection
        from agents.browser_agent.nodes.element_detection_node import element_detection_node

        detection_result = element_detection_node(state)
        state.detected_elements = detection_result.get("detected_elements", [])

        # Call model_node - agent should scroll now
        result = model_node(state)

        # Extract agent's response
        assert "messages" in result
        ai_message = result["messages"][0]
        assert isinstance(ai_message, AIMessage)

        tool_names = [tc["name"] for tc in ai_message.tool_calls] if ai_message.tool_calls else []

        print(f"\nAgent decision: {ai_message.content[:150]}")
        print(f"Tools called: {tool_names}")
        if ai_message.tool_calls:
            for tc in ai_message.tool_calls:
                print(f"  - {tc['name']}({tc.get('args', {})})")

        # Verify agent calls scroll (should scroll to get remaining 8 messages)
        assert "scroll" in tool_names, (
            f"Agent should call scroll to load 8 more messages.\n"
            f"Instead called: {tool_names}\n"
            f"Already collected 12/20, need to scroll for more."
        )

        # Find scroll tool call
        scroll_call = next((tc for tc in ai_message.tool_calls if tc["name"] == "scroll"), None)
        assert scroll_call is not None

        # Verify scroll arguments
        scroll_args = scroll_call.get("args", {})
        print(f"\n📋 Scroll args: {scroll_args}")

        # NEW FEATURE TEST: Check if agent uses coordinates for targeted scrolling
        if "x" in scroll_args and "y" in scroll_args and scroll_args.get("x") is not None:
            x = scroll_args["x"]
            y = scroll_args["y"]

            print(f"✅ NEW FEATURE: Agent used targeted scrolling at ({x}, {y})")

            # Verify coordinates target the message area (right side, not chat list)
            # Message area: X > 30 (right of chat list), Y around 40-60 (middle)
            assert 30 <= x <= 100, f"X={x} should target message area (30-100, recommended 60)"
            assert 20 <= y <= 80, f"Y={y} should target middle area (20-80, recommended 50)"

            print(f"✅ Coordinates correctly target message area (not chat list)")
        else:
            # Backward compatible: scroll without coordinates still works
            print("⚠️  Agent scrolled without coordinates (backward compatible)")
            print("    Ideal: scroll(direction='up', amount=800, x=60, y=50)")
            print("    This test passes but encourages coordinate-based scrolling")

        # Verify direction is UP (to load older messages)
        assert scroll_args.get("direction") == "up", (
            f"Should scroll UP to load older messages, got: {scroll_args.get('direction')}"
        )

        print("\n" + "=" * 80)
        print("✅ TEST PASSED: Agent scrolls after collecting initial messages")
        if scroll_args.get("x") is not None:
            print(f"✅ BONUS: Uses targeted scrolling at ({scroll_args['x']}, {scroll_args['y']})")
        print("=" * 80)

    def test_agent_avoids_duplicate_collection(
        self, whatsapp_instruction: str, initial_screenshot: str
    ):
        """Test that agent does NOT re-collect data from the same chat/location.

        This is the CRITICAL test for preventing duplicate collections.

        Scenario:
        1. Agent has loaded skill and opened a chat
        2. Agent collected messages from this chat (e.g., "PAKE WA" - 5 messages)
        3. ToolMessage confirmed successful collection
        4. Screenshot STILL shows the SAME chat (no UI change)
        5. Agent should realize it already collected and MOVE ON:
           - Option A: Scroll to see NEW messages (older/newer)
           - Option B: Click DIFFERENT chat to explore
           - Option C: Report task progress/completion
        6. Agent should NOT call collect_data() again with same content

        This tests the prompt engineering in system.prompt.md:
        - "Check conversation history - Did you already call collect_data?"
        - "Track what you collected - Which chats you already collected from"
        - "Move to unexplored areas - If you already collected from current location"
        """
        # Load skill content
        from pathlib import Path
        skill_path = Path(__file__).parent.parent.parent / "src" / "agents" / "browser_agent" / "prompts" / "skills" / "whatsapp-web.skill.prompt.md"
        with open(skill_path, "r") as f:
            skill_content = f.read()

        # Use ss-4.png (PAKE WA chat open with visible messages)
        chat_screenshot_path = IMAGES_DIR / "ss-4.png"
        assert chat_screenshot_path.exists(), f"Test image not found: {chat_screenshot_path}"
        chat_screenshot = load_image_as_data_url(chat_screenshot_path)

        # Build conversation: agent opened chat and ALREADY collected data
        messages = [
            HumanMessage(
                content=[
                    {"type": "text", "text": whatsapp_instruction},
                    {"type": "image_url", "image_url": {"url": initial_screenshot}},
                ]
            ),
            # Agent loaded skill
            AIMessage(
                content="Loading WhatsApp skill.",
                tool_calls=[{"id": "call_1", "name": "load_skill", "args": {"skill_name": "whatsapp-web"}}],
            ),
            ToolMessage(content=skill_content, tool_call_id="call_1"),
            # Agent clicked on PAKE WA chat
            AIMessage(
                content="I see PAKE WA chat in the list. I will click it to open.",
                tool_calls=[{"id": "call_2", "name": "click", "args": {"x": 20, "y": 45}}],
            ),
            ToolMessage(content="Clicked at (20, 45)", tool_call_id="call_2"),
            # Agent ALREADY collected 12 messages from this chat (ALL visible messages in ss-4.png)
            AIMessage(
                content="I see PAKE WA chat with 12 visible messages. I will collect them (12/20).",
                tool_calls=[{
                    "id": "call_3",
                    "name": "collect_data",
                    "args": {
                        "data": [
                            "WhatsApp Messages | PAKE WA → 12 messages (12/20): "
                            "[User]: Mau esuk ki Mas (05:47) | "
                            "[PAKE WA]: Kok iso boso jowo sisan yo? (10:04) | "
                            "[User]: Jajal upload en neng YouTube pak (10:04) | "
                            "[User]: Kek ono gambar2 AI (10:04) | "
                            "[PAKE WA]: Ngerti kanggo sopo mas lagu kwi? (10:10) | "
                            "[User]: sek lagi tak rungokne (10:11) | "
                            "[User]: dinggo lek to kah? (10:12) | "
                            "[User]: ref e marai nangis.. progressi chord e api pak (10:13) | "
                            "[User]: wes tak rungokne sampek bar (10:14) | "
                            "[PAKE WA]: Yo e (10:24) | "
                            "[PAKE WA]: Makan di mana?? (12:45) | "
                            "[User]: Neng warung mau pak (13:12)"
                        ]
                    }
                }],
            ),
            # ✅ IMPORTANT: ToolMessage confirms collection was successful
            ToolMessage(
                content="Successfully collected 12 items. Data submitted for processing.",
                tool_call_id="call_3"
            ),
        ]

        # State: SAME screenshot (chat still showing same messages, no UI change)
        state = AgentState(
            messages=messages,
            current_screenshot=chat_screenshot,  # Still showing PAKE WA chat
            viewport=Viewport(width=1280, height=800),
            detected_elements=[],
        )

        # Run element detection
        from agents.browser_agent.nodes.element_detection_node import element_detection_node
        detection_result = element_detection_node(state)
        state.detected_elements = detection_result.get("detected_elements", [])

        # Call model_node - agent should MOVE ON, not re-collect
        result = model_node(state)

        # Extract agent's response
        assert "messages" in result
        ai_message = result["messages"][0]
        assert isinstance(ai_message, AIMessage)

        tool_names = [tc["name"] for tc in ai_message.tool_calls] if ai_message.tool_calls else []

        print("\n" + "=" * 80)
        print("AGENT DECISION AFTER SUCCESSFUL COLLECTION:")
        print("=" * 80)
        print(f"Agent reasoning: {ai_message.content}")
        print(f"Tools called: {tool_names}")
        if ai_message.tool_calls:
            for tc in ai_message.tool_calls:
                print(f"  - {tc['name']}({tc.get('args', {})})")
        print("=" * 80)

        # CRITICAL ASSERTION: Agent should NOT call collect_data again
        assert "collect_data" not in tool_names, (
            f"❌ DUPLICATE COLLECTION DETECTED!\n"
            f"Agent already collected from PAKE WA chat (12 messages - ALL visible).\n"
            f"ToolMessage confirmed: 'Successfully collected 12 items.'\n"
            f"Screenshot STILL shows SAME chat with SAME 12 messages.\n"
            f"Agent should MOVE ON (scroll or click next chat), NOT re-collect.\n"
            f"Instead, agent called: {tool_names}\n"
            f"Reasoning: {ai_message.content}\n"
            f"\n"
            f"Expected behavior:\n"
            f"  - Option A: scroll (to see NEW older/newer messages beyond the 12)\n"
            f"  - Option B: click (to open DIFFERENT chat)\n"
            f"  - Option C: Text response (report progress: '12/20 collected, moving to next chat')\n"
        )

        # POSITIVE ASSERTION: Agent should move on
        valid_actions = ["scroll", "click", "screenshot"]
        has_valid_action = any(tool in tool_names for tool in valid_actions)

        # Allow text-only response if agent is reporting completion/progress
        has_text_response = bool(ai_message.content and len(ai_message.content.strip()) > 10)

        assert has_valid_action or has_text_response, (
            f"Agent avoided duplicate collection ✅ but didn't move on.\n"
            f"Expected: scroll (for more messages) OR click (next chat) OR text response (progress report)\n"
            f"Got: {tool_names if tool_names else 'text only: ' + ai_message.content}"
        )

        # Success messages
        print("\n" + "=" * 80)
        print("✅ TEST PASSED: Agent avoids duplicate collection")
        print(f"✅ Agent recognized it already collected from this chat")
        print(f"✅ Agent moved on with: {tool_names if tool_names else 'text response'}")
        if "scroll" in tool_names:
            print("   → Agent will scroll to see NEW messages (good!)")
        elif "click" in tool_names:
            print("   → Agent will click DIFFERENT chat (good!)")
        elif has_text_response:
            print("   → Agent reported progress/completion (good!)")
        print("=" * 80)
