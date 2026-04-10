from werkzeug.security import generate_password_hash

# We explicitly tell it to use 'pbkdf2:sha256' to avoid the '32768' error
safe_hash = generate_password_hash('admin123', method='pbkdf2:sha256')
print(safe_hash)