from main import generate_enemies
try:
    print(generate_enemies(1, 'test'))
except Exception as e:
    import traceback
    traceback.print_exc()