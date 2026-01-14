# WhatsApp Web Skill

## Page State Detection (Check First!)

Look at the screenshot and identify the current state:

### State 1: LOADING
**What you see:**
- Centered WhatsApp logo (green circle with phone icon)
- Text "End-to-end encrypted" below it
- NO chat list visible
- Blank background

**Action:** `wait(3000)` → `screenshot()` (max 3 times total)

---

### State 2: LOADED (Chat List Visible)
**What you see:**
- Left sidebar with chat list
- Contact/group names visible (AHMAD SOMPRET, PAKE WA, etc.)
- Search bar at top
- Profile pictures next to names
- Timestamps visible
- **Note:** Green notification banners like "Turn on background sync" mean page IS loaded!

**Action:** Proceed to collect messages

---

### State 3: QR CODE / Login
**What you see:**
- QR code in center
- "Scan to log in" or "Link with phone" text

**Action:** `collect_data(["error: WhatsApp Web requires QR code authentication"])`

---

## Message Collection (When LOADED)

1. **Click first chat** in left sidebar (around x=10, y=25)
2. **Wait 500ms** for chat to open
3. **Read messages** from screenshot (sender, text, time)
4. **Go back** to chat list (click left sidebar x=7, y=10)
5. **Repeat** for top 5 chats
6. **Submit data** with `collect_data([message strings])`

## Important

- **DON'T** confuse notification banners with loading screens
- **DO** count visible chat items - if you see 5+ chat names, page is loaded
- **DON'T** wait more than 3 times on loading screen
- **DO** click and interact if you see the chat list
