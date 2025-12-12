
import math

class MeshGridMapper:
    def __init__(self):
        self.min_x = float('inf')
        self.max_x = float('-inf')
        self.min_y = float('inf')
        self.max_y = float('-inf')
        self.mapping = {} # mesh_code -> (col_x, row_y)
        self.reverse_mapping = {} # (col_x, row_y) -> mesh_code
        self.cols = 0
        self.rows = 0

    def fit(self, mesh_codes):
        """
        Analyzes a list of mesh codes to determine grid bounds and create a mapping.
        Assumes all mesh codes are of the same level (e.g., all 9-digit or all 8-digit).
        """
        coords = []
        for code in mesh_codes:
            code = str(code)
            # Basic parsing for Standard Mesh
            # 1st (4): YYXX
            # 2nd (2): yx
            # 3rd (2): yx
            # 4th (1): n (1=SW, 2=SE, 3=NW, 4=NE) -> corresponds to 2x2 subgrid
            
            # We will convert everything to a global relative coordinate system based on the smallest unit
            # For 9-digit (4th mesh), the unit is 1/2 of 3rd mesh.
            
            y1 = int(code[0:2])
            x1 = int(code[2:4])
            y2 = int(code[4:5])
            x2 = int(code[5:6])
            
            y3 = 0
            x3 = 0
            y4 = 0
            x4 = 0
            
            if len(code) >= 8:
                y3 = int(code[6:7])
                x3 = int(code[7:8])
            
            if len(code) >= 9:
                n = int(code[8:9])
                # 1: SW (0,0), 2: SE (1,0), 3: NW (0,1), 4: NE (1,1)
                if n == 1: y4, x4 = 0, 0
                elif n == 2: y4, x4 = 0, 1
                elif n == 3: y4, x4 = 1, 0
                elif n == 4: y4, x4 = 1, 1
                
            # Calculate absolute index factors
            # Level 1: 80km x 80km roughly. 
            # Level 2: Divide by 8 -> 10km. (Index 0-7)
            # Level 3: Divide by 10 -> 1km. (Index 0-9)
            # Level 4: Divide by 2 -> 500m. (Index 0-1)
            
            # Global X index = (x1 * 80 * 10 * 2) + (x2 * 10 * 2) + (x3 * 2) + x4
            # Global Y index = (y1 * 80 * 10 * 2) + (y2 * 10 * 2) + (y3 * 2) + y4
            # Wait, 1st mesh isn't 0-based index. It starts from 30 usually. 
            # We just need relative differences, so this "Global Index" formula works for sorting/bounds.
            
            gx = (x1 * 8 * 10 * 2) + (x2 * 10 * 2) + (x3 * 2) + x4
            gy = (y1 * 8 * 10 * 2) + (y2 * 10 * 2) + (y3 * 2) + y4
            
            coords.append((code, gx, gy))
            
            if gx < self.min_x: self.min_x = gx
            if gx > self.max_x: self.max_x = gx
            if gy < self.min_y: self.min_y = gy
            if gy > self.max_y: self.max_y = gy
            
        # Create normalized mapping (0 to Width-1, 0 to Height-1)
        self.cols = (self.max_x - self.min_x) + 1
        self.rows = (self.max_y - self.min_y) + 1
        
        for code, gx, gy in coords:
            # Grid logic usually places (0,0) at Top-Left or Bottom-Left.
            # Array logic: row 0 is usually top.
            # Map logic: Y increases North.
            # Let's align with Array logic: (row, col).
            # If we want visual consistency, row 0 should be North (Max Y).
            # let row = self.max_y - gy
            # let col = gx - self.min_x
            
            col = gx - self.min_x
            row = self.max_y - gy # Invert Y so 0 is top
            
            self.mapping[code] = (col, row)
            self.reverse_mapping[(col, row)] = code

    def get_grid_coords(self, mesh_code):
        return self.mapping.get(str(mesh_code))
        
    def get_mesh_code(self, col, row):
        return self.reverse_mapping.get((col, row))
