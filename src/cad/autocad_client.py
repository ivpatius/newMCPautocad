import comtypes.client
import time

class AutoCADClient:
    def __init__(self):
        self.app = None
        self.doc = None
        self.model_space = None

    def connect(self):
        """Connect to a running instance of AutoCAD."""
        try:
            self.app = comtypes.client.GetActiveObject("AutoCAD.Application")
            self.doc = self.app.ActiveDocument
            self.model_space = self.doc.ModelSpace
            print("Successfully connected to AutoCAD.")
            return True
        except Exception as e:
            print(f"Error connecting to AutoCAD: {e}")
            return False

    def add_line(self, start_point, end_point):
        """Add a line to the model space."""
        if not self.model_space:
            return None
        # points are tuples (x, y, z)
        return self.model_space.AddLine(comtypes.automation.VARIANT(start_point), 
                                        comtypes.automation.VARIANT(end_point))

    def add_circle(self, center, radius):
        """Add a circle to the model space."""
        if not self.model_space:
            return None
        return self.model_space.AddCircle(comtypes.automation.VARIANT(center), radius)

    def add_point(self, point):
        """Add a point to the model space."""
        if not self.model_space:
            return None
        return self.model_space.AddPoint(comtypes.automation.VARIANT(point))

    def add_arc(self, center, radius, start_angle, end_angle):
        """Add an arc to the model space."""
        if not self.model_space:
            return None
        return self.model_space.AddArc(comtypes.automation.VARIANT(center), radius, start_angle, end_angle)

    def add_spline(self, points):
        """Add a spline to the model space from a list of points."""
        try:
            if not self.model_space:
                return None
            flattened_points = [p for pt in points for p in pt]
            start_tan = comtypes.automation.VARIANT([0.0, 0.0, 0.0])
            end_tan = comtypes.automation.VARIANT([0.0, 0.0, 0.0])
            return self.model_space.AddSpline(comtypes.automation.VARIANT(flattened_points), start_tan, end_tan)
        except Exception as e:
            print(f"Error adding spline: {e}")
            return None

    def trim(self):
        """Invoke the TRIM command in AutoCAD. 
        Note: Trim usually requires interactive selection, but we can send command strings.
        """
        print("Sending TRIM command to AutoCAD...")
        self.send_command("_TRIM")

    def send_command(self, command):
        """Send a raw command to AutoCAD."""
        try:
            if self.doc:
                # Use \r to simulate Enter
                self.doc.SendCommand(f"{command} ")
                return True
        except Exception as e:
            print(f"Error sending command: {e}")
            return False
        return False

if __name__ == "__main__":
    client = AutoCADClient()
    if client.connect():
        # Example: Draw a simple line
        client.add_line((0, 0, 0), (10, 10, 0))
        client.add_circle((5, 5, 0), 2.5)
