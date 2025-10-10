class TelemetryBase:
    def poll(self) -> dict:
        """Powinno zwrócić: game_time_unix:int, speed_kmh:float, engine_on:bool, parking_brake:bool, paused:bool"""
        raise NotImplementedError
