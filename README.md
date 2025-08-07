This is a simple tool designed mostly for calculating the percentage of eroded soil in fields, but I imagine it can have many different uses  
**What this tool does:**  
1. At first, you select an image from your computer
2. Then you draw a polygon using the Plot line tool enclosing specified part of your image that you want to check
3. If you happen to miss a point, you can freely remove it by right clicking it
4. After selecting Pick color tool, you navigate to a specific color you want to highlight with your cursor and click on it
5. You can adjust the sensitivity using the top slider, the mask will dynamically adjust
6. And lastly you click calculate area which will calculate the percentage of highlighted pixels
7. If you want to hide the line or highlight mask, you can use the provided checkboxes

**Useful Info**:
1. **THIS APP IS A PROTOTYPE**
2. If you're not running this through an exe, you can change the distance from which clicking an anchor point would count on line 25 in the code
3. The output messages (prints) are handled through the console for now since this is a prototype for now

**Known bugs**:  
1. Weird discoloration issue caused by numpy. Open to any suggestions
