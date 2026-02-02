Azur Lane Automation: Login Flow
This document details the exact sequence of actions, coordinates, and timings used to successfully log in to Azur Lane using the Android-Mobile-MCP server.

Coordinate System
Resolution Base: 1280x720 (Standard Landscape)
Method: Coordinate-based interaction (Bypassing accessibility node limitations for Game Views)
Step-by-Step Flow
1. Launch Application
Action: Click App Icon
Coordinates: 
(1080, 182)
Context: Locates "Azur Lane" on the Android Home Screen.
Wait: 15 seconds (Allow initial asset loading)
2. "Press to Start" Screen
Action: Tap Center Screen
Coordinates: 
(640, 360)
Reasoning: The "Press to Start" overlay is a full-screen Unity element. Clicking dead center reliably triggers the start event.
Wait: 10 seconds (Server connection handshake)
3. Server Selection / Login Confirmation
Action: Tap Center Screen
Coordinates: 
(640, 360)
Reasoning: Confirms the selected server (e.g., "Washington") and proceeds to the main lobby.
Wait: 20 seconds (Lobby asset loading)
4. Handle Announcements (Patch Notes)
Action: Close Popup
Coordinates: 
(1230, 85)
Method: 
mobile_swipe
 (Start: 1230,85 -> End: 1230,85)
Reasoning: The "Close" (X) button is located in the top-right corner. Used a zero-distance swipe to simulate a tap because specific Unity UI elements were not clickable via standard accessibility mapping.
Current State
Status: Successfully Logged In
Current Screen: Main Lobby (Secretary Ship Visible)
Next Step: Verifying "Battle" menu entry.
