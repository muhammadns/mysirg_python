def show_details(name, age, city, profession):
    print(f"Name: {name}")
    print(f"Age: {age}")
    print(f"City: {city}")
    print(f"Profession: {profession}")

args = ["John Doe", 30, "New York", "Engineer"]

kwargs = {
    "name": "Smith",
    "age": 28,
    "city": "Los Angeles",
    "profession": "Designer"
}

show_details(*args)  # Unpacking the list into positional arguments
print()  # Adding a blank line for better readability
show_details(**kwargs)  # Unpacking the dictionary into keyword arguments
