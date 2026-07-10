from app import app

print("Registered Routes:")
for rule in app.url_map.iter_rules():
    print(f"Path: {rule.rule} | Methods: {list(rule.methods)} | Endpoint: {rule.endpoint}")
