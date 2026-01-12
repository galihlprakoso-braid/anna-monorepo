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

Use the detected UI elements to find:

- **Search bar**: Look for Input element with caption containing "Search", "Ask Meta AI", or similar, typically in the left sidebar
- **Message input**: Look for Input element near the bottom of the chat view, caption may include "Type a message" or similar
- **Send button**: Look for Button element with send icon or caption, positioned to the right of the message input
- **Chat list items**: Text elements in the left sidebar showing contact names and recent messages
- **New chat button**: Button or Icon in the top-left area of the left sidebar
- **Attach button**: Button or Icon near the message input (usually left of input)

## Interaction Patterns

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

### Handling Pop-ups
- **QR Code screen**: If you see QR code, inform user they need to scan it manually
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
