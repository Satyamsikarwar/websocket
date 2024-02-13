from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
import json

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Chat</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
        }

        .container {
            display: flex;
            height: 100vh;
        }

        .left {
            flex: 1;
            border-right: 1px solid #ccc;
            padding: 20px;
        }

        .right {
            flex: 2;
            padding: 20px;
        }

        h1, h2 {
            color: #333;
        }

        ul {
            list-style-type: none;
            padding: 0;
        }

        ul li {
            margin-bottom: 10px;
            cursor: pointer;
            padding: 10px;
            border-radius: 5px;
        }

        #activeUsersList li:hover {
            background-color: #f0f0f0;
        }

        #messageForm {
            margin-top: 20px;
        }

        input[type="text"], button {
            padding: 10px;
            font-size: 16px;
            border: 1px solid #ccc;
            border-radius: 5px;
        }

        input[type="text"] {
            width: calc(100% - 80px);
            margin-right: 10px;
        }

        button {
            background-color: #007bff;
            color: #fff;
            border: none;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }

        button:hover {
            background-color: #0056b3;
        }

        #rightPanel {
            display: none;
        }

        #rightPanel.show {
            display: block;
        }

        #userMessages {
            list-style-type: none;
            padding: 0;
        }

        .messageBox {
            background-color: #f0f0f0;
            padding: 10px;
            border-radius: 10px;
            margin-bottom: 10px;
        }

        .ownMessage {
            background-color: #cce5ff;
        }
    </style>
</head>
<body>
<h1>WebSocket Chat</h1>
<div class="container">
    <div class="left">
        <h2>Active Users</h2>
        <ul id="activeUsersList">
            <!-- Active users will be dynamically added here -->
        </ul>
    </div>
    <div class="right" id="rightPanel">
        <h2 id="userHeader"></h2>
        <ul id="userMessages">
            <!-- Messages will be dynamically added here -->
        </ul>
        <div id="messageForm">
            <form onsubmit="sendMessage(event)">
                <input type="hidden" id="recipientId">
                <input type="text" id="messageText" autocomplete="off" placeholder="Type your message..."/>
                <button>Send</button>
            </form>
        </div>
    </div>
</div>
<script>
    var ws;
    var clientId = new Date().getTime(); // Generate unique client ID based on current time

    function connectWebSocket() {
        ws = new WebSocket("ws://localhost:8000/ws/" + clientId);
        ws.onopen = function(event) {
            console.log("WebSocket connected.");
        };
        ws.onmessage = function(event) {
            console.log(event);
            try {
                var data = JSON.parse(event.data);
                handleMessage(data);
            } catch (error) {
                console.error("Error parsing JSON:", error);
                // Handle non-JSON messages here
                var messages = document.getElementById('userMessages');
                var message = document.createElement('li');
                message.className = "messageBox";
                var content = document.createTextNode(event.data);
                message.appendChild(content);
                messages.appendChild(message);
            }
        };
        ws.onclose = function(event) {
            console.log("WebSocket connection closed.");
        };
    }

    function handleMessage(data) {
        if (data.active_users) {
            updateActiveUsersList(data.active_users);
        } else if (data.type === "message") {
            console.log(data.content);
            var messages = document.getElementById('userMessages');
            var message = document.createElement('li');
            message.className = "messageBox";
            if (data.sender_id === clientId) {
                message.classList.add("ownMessage");
                message.textContent = "(You) " + data.content;
            } else {
                message.textContent = data.content;
            }
            messages.appendChild(message);
        } else {
            console.log("Received unknown message type:", data);
        }
    }

    function updateActiveUsersList(activeUsers) {
        var activeUsersList = document.getElementById('activeUsersList');
        activeUsersList.innerHTML = ''; // Clear existing list
        activeUsers.forEach(function(user) {
            var listItem = document.createElement('li');
            if (user.toString() === clientId.toString()) {
            console.log("user:", user);
            console.log("clientId:", clientId.toString());
            console.log("you are the current user");
            listItem.textContent = "You (" + user + ")";
        } else {
            console.log("user:", user);
            console.log("clientId:", clientId.toString());
            console.log("You are not the current user");
            listItem.textContent = user;
        }
            listItem.onclick = function() {
                showMessageForm(user);
            };
            activeUsersList.appendChild(listItem);
        });
    }

    function showMessageForm(user) {
        document.getElementById('userHeader').textContent = "Messages for " + user;
        var recipientInput = document.getElementById('recipientId');
        recipientInput.value = user;
        var rightPanel = document.getElementById('rightPanel');
        rightPanel.style.display = 'block';
        var messages = document.getElementById('userMessages');
        messages.innerHTML = ''; // Clear existing messages
        // Here you can make an API call to fetch previous messages for the selected user and populate the messages list
    }

    function sendMessage(event) {
        var recipientId = document.getElementById("recipientId").value;
        var messageText = document.getElementById("messageText").value;
        ws.send(JSON.stringify({"recipient_id": recipientId, "message": messageText}));
        // Display the sent message on the sender's side as well
        var messages = document.getElementById('userMessages');
        var message = document.createElement('li');
        message.className = "messageBox ownMessage"; // Mark it as the sender's own message
        message.textContent = "(You) " + messageText;
        messages.appendChild(message);
        document.getElementById("messageText").value = '';
        event.preventDefault();
    }
    connectWebSocket();
</script>
</body>
</html>
"""
class ConnectionManager:
    def __init__(self):
        self.active_connections = {}
        self.active_client_ids = set()

    async def connect(self, websocket: WebSocket, client_id: int):
        try:
            await websocket.accept()
        except WebSocketDisconnect:
            raise HTTPException(status_code=400, detail="WebSocket connection failed.")
        self.active_connections[client_id] = websocket
        self.active_client_ids.add(client_id)
        await self.send_active_users()

    async def send_private_message(self, recipient_id: int, message: str):
        if recipient_id not in self.active_connections:
            raise HTTPException(status_code=400, detail="Recipient is not connected.")
        websocket = self.active_connections[recipient_id]
        try:
            await websocket.send_text(json.dumps({"type": "message", "content": message}))
        except WebSocketDisconnect:
            raise HTTPException(status_code=400, detail="Failed to send message.")

    async def disconnect(self, client_id: int):
        if client_id not in self.active_connections:
            raise HTTPException(status_code=400, detail="Client is not connected.")
        del self.active_connections[client_id]
        self.active_client_ids.remove(client_id)
        await self.send_active_users()

    async def send_active_users(self):
        active_users = list(self.active_client_ids)
        for connection in self.active_connections.values():
            try:
                await connection.send_text(json.dumps({"active_users": active_users}))
            except WebSocketDisconnect:
                raise HTTPException(status_code=400, detail="Failed to send active users list.")

manager = ConnectionManager()

@app.get("/")
async def get():
    return HTMLResponse(html)

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    try:
        await manager.connect(websocket, client_id)
        while True:
            data = await websocket.receive_text()
            data_dict = json.loads(data)
            print(data_dict)
            recipient_id = int(data_dict.get("recipient_id"))  # Convert recipient_id to an integer
            message = data_dict.get("message")
            if recipient_id is None or message is None:
                print('user not found')
                raise HTTPException(status_code=400, detail="Invalid data format.")
            await manager.send_private_message(recipient_id, message)
    except WebSocketDisconnect:
        await manager.disconnect(client_id)
    except Exception as e:
        # Handle unexpected exceptions
        print(f"Unexpected error: {e}")