class FakeNotificationService:
    def __init__(self):
        self.sent = []

    async def send(self, recipient: str, message: str) -> None:
        self.sent.append(
            {
                "recipient": recipient,
                "message": message,
            }
        )