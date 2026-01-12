# WhatsApp Web Automation Skill

You are now specialized in automating WhatsApp Web (web.whatsapp.com). This skill provides detailed knowledge about WhatsApp Web's interface structure and interaction patterns.

## Interface Structure

### Main Layout (0-100 grid coordinates)
- **Left Sidebar** (x: 0-25): Contains chat list, search, and navigation
  - Search bar: x=12, y=8
  - Chat list: x=12, y=15-90
  - New chat button: x=5, y=5 (top-left)

- **Chat View** (x: 25-100): Active conversation area
  - Contact name/header: x=62, y=5
  - Message area: x=62, y=15-85
  - Message input box: x=62, y=92
  - Attach button: x=30, y=92
  - Send button: x=95, y=92

### Common Element Positions
- **Search contacts**: Click x=12, y=8, then type
- **Open chat**: Click on contact in list (x=12, y varies by position)
- **Type message**: Click x=62, y=92, then type
- **Send message**: Click x=95, y=92 OR press Enter after typing
- **Scroll messages**: Use scroll(direction="up") in chat area

## Interaction Patterns

### Sending a Message
1. **Find/search contact**:
   - Click search bar (x=12, y=8)
   - Type contact name
   - Wait 500ms for search results

2. **Open chat**:
   - Click on contact (typically x=12, y=20 for first result)
   - Wait 700ms for chat to load

3. **Type and send**:
   - Click message input (x=62, y=92)
   - Type message text
   - Click send button (x=95, y=92) OR type_text("\n") to press Enter

### Reading Messages
1. **Scroll to see history**:
   - Use scroll(direction="up", amount=500) to see older messages
   - Take screenshot to verify content

2. **Finding specific chats**:
   - Use search bar (x=12, y=8) to filter chat list
   - Scroll chat list if needed (x=12, y=50, scroll direction="down")

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
