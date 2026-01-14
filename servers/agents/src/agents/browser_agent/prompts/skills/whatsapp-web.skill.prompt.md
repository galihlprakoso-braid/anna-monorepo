# WhatsApp Web Automation Skill

You are now specialized in automating WhatsApp Web (web.whatsapp.com). This skill provides detailed knowledge about WhatsApp Web's interface structure and interaction patterns.

## Interface Structure

### Main Layout
- **Left Sidebar**: Contains chat list, search, and navigation
  - Located on the left side of the screen (approximately x: 0-25)
  - Contains search bar at the top
  - Chat list items below search
  - New chat button in top-left corner

- **Chat View**: Active conversation area
  - Located on the right side (approximately x: 25-100)
  - Contact name/header at the top
  - Message area in the center
  - Message input box at the bottom
  - Attach button and send button near input box

### Element Identification

**Visual Recognition (from screenshot):**
Look at the screenshot image to identify these elements visually:
- **Search bar**: Text input at top of left sidebar (may say "Ask Meta AI" or "Search")
- **Message input**: Text input at bottom of chat area (may say "Type a message")
- **Send button**: Icon/button to the right of message input
- **Chat list items**: Profile pictures with contact names in left sidebar
- **Notification banners**: Yellow/green banners with dismiss buttons

**Using Detected Elements for Coordinates:**
Once you visually identify WHAT you want to click, use detected elements to find WHERE to click:
- **Left sidebar elements**: Typically at x=0-25
- **Center/chat area elements**: Typically at x=30-70
- **Right side elements**: Typically at x=75-100
- **Top of screen**: y=0-20
- **Bottom of screen**: y=80-100

**Note**: Element captions may be generic ("UI element"). Match the element's grid position to what you see in the screenshot to determine which element to click.

## Interaction Patterns

### Before Any Action - Check Page State (Use Screenshot Image)
**IMPORTANT: Look at the SCREENSHOT to determine page state, NOT the detected elements.**

**Visually identify in the screenshot:**
- **Loading screen**: Centered WhatsApp logo, "End-to-end encrypted" text, no chat list visible
- **QR code screen**: Large QR code in center, instructions to scan with phone
- **Fully loaded interface**: Left sidebar with chat list visible, contact names/avatars shown

**If loading/QR screen**: Use `wait` for 3000-5000ms, then `screenshot` again
**If fully loaded**: Proceed with your task!

### Sending a Message
1. **Find/search contact**:
   - Locate the search bar in detected elements (look for Input with "Search" or "Ask Meta AI")
   - Click the search bar coordinates
   - Type contact name
   - Wait 500ms for search results

2. **Open chat**:
   - Find the contact in detected elements (look for Text with matching contact name)
   - Click on the contact's coordinates
   - Wait 700ms for chat to load

3. **Type and send**:
   - Find the message input in detected elements (look for Input near bottom)
   - Click the message input coordinates
   - Type message text
   - Find the send button (look for Button near input) and click OR type_text("\n") to press Enter

### Reading Messages
1. **Scroll to see history**:
   - Use scroll(direction="up", amount=500) to see older messages in the chat area
   - Take screenshot to verify content and get updated element positions

2. **Finding specific chats**:
   - Locate and click the search bar from detected elements
   - Type to filter chat list
   - If needed, scroll the chat list area using scroll(direction="down")

### Collecting Messages from Multiple Chats
**For data collection tasks** ("collect messages", "get WhatsApp data"):

1. **Visually verify interface is loaded** (look at screenshot: can you see chat list on left?)
2. **Look at the screenshot to identify chat items**: You'll see contact names, profile pictures, and message previews in the left sidebar
3. **Find coordinates for clicking**:
   - The left sidebar is typically at x=0-25 in the grid
   - Use detected elements in that region to get accurate click coordinates
   - Look at the screenshot to decide WHICH chat to click, use detected elements for WHERE to click
4. **Click a chat**: Use coordinates from detected elements in left sidebar area
5. **Wait for chat to load**: Use `wait` for 700-1000ms
6. **Take screenshot**: See the chat messages
7. **Read messages from screenshot**: Look at the message content, sender names, timestamps in the image
8. **Collect data**: Use `collect_data` tool with what you READ from the screenshot
9. **Click next chat**: Go back to left sidebar, click another chat
10. **Repeat** until sufficient data collected

**Key principle**: Look at screenshot to UNDERSTAND and DECIDE, use detected elements to CLICK accurately.

### Initial Page Load & State Detection

**CRITICAL: Use the SCREENSHOT IMAGE to determine page state**

Look at the screenshot and visually identify:

#### Loading Screen (NOT ready):
- **What you see in screenshot**: WhatsApp logo centered, "End-to-end encrypted" text, possibly a progress indicator
- **Visual appearance**: Mostly empty screen with just the logo
- **Action**: Use `wait` for 3000-5000ms, then `screenshot` again

#### QR Code Screen (NOT ready):
- **What you see in screenshot**: Large QR code in center, instructions to scan with WhatsApp mobile app
- **Visual appearance**: QR code is prominent, no chat list visible
- **Action**: Inform user they need to scan the QR code to log in

#### Fully Loaded Interface (READY):
- **What you see in screenshot**: Left sidebar with chat list (contact names, profile pictures, message previews), main chat area on right
- **Visual appearance**: Two-column layout with visible conversations on the left
- **Note**: Even if right side shows "Download WhatsApp for Mac", if you SEE the chat list on the left, you're ready!
- **Action**: Proceed with your task!

#### Using Detected Elements for Clicking:
Once you've visually confirmed the interface is loaded, use the detected elements to find accurate coordinates:
- Elements at x=0-25 are in the left sidebar (chat list area)
- Match what you SEE in the screenshot to element coordinates for accurate clicking

### Handling Pop-ups
- **QR Code screen**: If you see QR code after the page loads, inform user they need to scan it manually to log in
- **Permission prompts**: Click "Allow" if appropriate (typically center screen)
- **Update notifications**: Click "Dismiss" or close button (top-right of modal)

## Important Notes

### Timing Considerations
- Always wait 500-1000ms after clicking to open a chat
- Wait 300-500ms after typing before sending
- Take screenshots frequently to verify state

### Visual Cues
- Selected chat has a light background (vs. dark for unselected)
- Unread messages show bold text and green badges
- Active input box shows a blinking cursor
- Sent messages appear on the right (x=70-95)
- Received messages appear on the left (x=30-60)

### Limitations
- Cannot access media/images directly (describe what you see in screenshots)
- Cannot make voice/video calls (inform user to do manually)
- Cannot modify WhatsApp settings (read-only automation)
- Cannot verify message delivery status beyond visual confirmation

## Error Recovery

### Common Issues
1. **Chat not loading**:
   - Wait longer (1500ms)
   - Take screenshot to verify
   - Try clicking chat again if needed

2. **Search not working**:
   - Clear search box first (click, select all, delete)
   - Retype search term
   - Verify search results in screenshot

3. **Message not sending**:
   - Verify input box is active (cursor visible)
   - Check if send button is enabled (not grayed out)
   - Retry send click or use Enter key

4. **Wrong chat opened**:
   - Use search to find correct contact
   - Verify chat header matches expected contact name

## Best Practices
- Always verify the active chat before sending messages
- Take screenshots before and after important actions
- Use search to find contacts instead of scrolling through long lists
- Wait for animations to complete before next action
- Inform user if manual intervention is required (QR code, permissions)

Remember: WhatsApp Web requires an active phone connection. If you see a "Phone not connected" message, inform the user to check their phone.
