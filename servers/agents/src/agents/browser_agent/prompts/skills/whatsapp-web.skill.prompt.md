# WhatsApp Web Skill

Generic knowledge for interacting with WhatsApp Web interface.

---

## Page States

WhatsApp Web has different states you may encounter:

### State: LOADING
**Visual indicators:**
- Centered WhatsApp logo (green circle with phone icon)
- Text "End-to-end encrypted" below logo
- NO chat list visible
- Blank/white background

**How to handle:** Wait for page to load, then take screenshot to check state

---

### State: LOADED (Chat List View)
**Visual indicators:**
- Left sidebar with chat list (vertical list of conversations)
- Contact/group names visible in list
- Search bar at top of sidebar
- Profile pictures next to contact names
- Timestamps on the right of each chat item
- **Note:** Green notification banners (e.g., "Turn on background sync") mean page IS loaded!

**UI Layout:**
- **Chat list**: Vertical list in left sidebar
  - Each chat item shows: profile picture, contact/group name, last message preview, timestamp
  - Chats are ordered by most recent activity
- **Search bar**: Located at top of left sidebar
- **Menu button**: Top-left corner (three dots icon)

**How to interact:**
- Click on chat items to open conversations
- Use search bar to find specific chats
- Scroll up/down in chat list to see more conversations

---

### State: CHAT VIEW (Conversation Open)
**Visual indicators:**
- Right side (or full screen on mobile) shows message thread
- Chat header at top with contact/group name and info
- Message bubbles (typically green for sent, white for received)
- Text input field at bottom
- Back arrow or chat list visible on left side

**UI Layout:**
- **Chat header**: Top of conversation, shows contact/group name, profile picture, status
- **Message area**: Center/right area showing conversation history
  - Sent messages: Usually on right side, green background
  - Received messages: Usually on left side, white/gray background
  - Each message shows: sender name (in groups), message text, timestamp
- **Back button**: Arrow or chat list area to return to chat list
- **Message input**: Bottom of screen for typing new messages
- **Scroll area**: Scroll up to load older messages

**How to interact:**
- Click back arrow or left sidebar area to return to chat list
- Scroll up to load older messages
- Read visible messages from screenshot (sender, text, timestamp)
- Click on message input to type (if needed)
- Send messages using send button

---

### State: QR CODE / Login Required
**Visual indicators:**
- QR code displayed in center of screen
- Text like "Scan to log in", "Link with phone", or "Use WhatsApp on your phone to scan this code"
- No chat list or messages visible

**How to handle:** This state requires manual user authentication with phone

---

## Spatial Layout & Coordinates

**Understanding WhatsApp Web's vertical layout (0-100 grid system):**

### Top Section (Y: 0-35)
- **Y coordinates 0-20:** Header area (logo, search bar, menu)
- **Y coordinates 20-35:** Notification banners (green/yellow alerts like "Turn on background sync")
- ⚠️ **WARNING:** This area contains UI chrome, NOT chat items

### Middle-Bottom Section (Y: 35-100)
- **Y coordinates 35-95:** Actual chat list area
- **Y coordinates 40-60:** First 3-4 chat items (typical target zone)
- **Y coordinates 60-85:** Chat items 5-10
- **Y coordinates 85-95:** Bottom chat items / scroll area

### Horizontal Layout (X coordinates)
- **X coordinates 0-30:** Left sidebar (where chat list is)
- **X coordinates 30-100:** Main content area (message view when chat is open)

---

## Scrolling Strategy

WhatsApp Web has **TWO independent scrollable areas** that require targeted scrolling:

### 1. Chat List (Left Sidebar)
**When to scroll:** To see more conversations beyond the visible ones
**Target coordinates:**
- X=15 (middle of left sidebar)
- Y=50 (middle of screen)
**Example:**
```
scroll(direction='down', amount=400, x=15, y=50)  # See more chats
scroll(direction='up', amount=400, x=15, y=50)    # Back to top of chat list
```

### 2. Message Area (Right Panel)
**When to scroll:** To load older messages within an open chat conversation
**Target coordinates:**
- X=60 (middle of message area)
- Y=50 (middle of screen)
**Example:**
```
scroll(direction='up', amount=800, x=60, y=50)    # Load older messages
scroll(direction='down', amount=800, x=60, y=50)  # See newer messages
```

### ⚠️ CRITICAL: Always Use Coordinates When Scrolling
- **Without coordinates:** `scroll(direction='up', amount=800)` → Scrolls entire window (UNPREDICTABLE)
- **With coordinates:** `scroll(direction='up', amount=800, x=60, y=50)` → Scrolls message area (PRECISE)

The coordinate-based approach ensures you scroll the correct area, not the entire page or wrong section.

---

### Clicking on Chat Items
When you need to click the first chat in the list:
- **Safe Y range:** 40-55 (well below any banners)
- **Safe X range:** 15-25 (centered in chat list area)
- **Example coordinates:** (18, 45) or (20, 48)

⚠️ **Common Mistakes to Avoid:**
1. **Clicking too high (Y < 35):** You'll hit notification banners or header elements instead of chat items
2. **Visual confusion:** The "first chat" appears near the top visually, but requires Y > 40 to avoid banner overlap
3. **After failed click:** If you click and don't see a chat open, move DOWNWARD (increase Y), not upward

---

## Common Interaction Patterns

### Opening a chat:
1. Ensure you're in LOADED state (chat list visible)
2. Identify and click on desired chat item in left sidebar
3. Wait briefly (1-5s) for chat to load
4. Take screenshot to verify messages are visible

### Reading messages:
1. Open the chat (see above)
2. Look at message bubbles in conversation area
3. Extract information: sender name, message text, timestamp
4. Scroll up if you need to see older messages
5. Scroll down to see newer messages

### Returning to chat list:
1. Click back arrow or left sidebar area
2. Wait briefly for transition
3. Take screenshot to confirm you're back at chat list

### Searching for a chat:
1. Click search bar at top of sidebar
2. Type search query
3. Wait for results to filter
4. Click on desired chat from filtered results

### Scrolling through messages:
1. To see older messages: `scroll(direction='up', amount=800, x=60, y=50)`
2. To see newer messages: `scroll(direction='down', amount=800, x=60, y=50)`
3. Messages load dynamically as you scroll
4. **Always use coordinates** (see Scrolling Strategy section above)

---

## Important Notes

- **Notification banners** (green bars at top) do NOT mean page is loading - they appear on loaded pages
- **Chat list visibility** is the key indicator that page is ready to interact with
- **Wait times**: Allow 300-500ms after clicks for UI transitions to complete
- **Message format**: Messages typically include sender name (in groups), text content, and timestamp
- **Visual confirmation**: Always take screenshots after actions to verify state changes
- **Screen variations**: UI layout may vary slightly based on screen size, but general structure remains consistent
