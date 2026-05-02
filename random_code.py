import random
import math

name = "Python Script"
numbers = [1, 5, 3, 9, 2]
result = sum(numbers) / len(numbers)

for i in range(3):
    print(f"Iteration {i}: {random.randint(1, 100)}")

print(f"Average: {result}")
