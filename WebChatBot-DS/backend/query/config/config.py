from dotenv import load_dotenv, dotenv_values
import os

# Xác định đường dẫn file .env
dotenv_path = os.path.join(os.path.dirname(__file__), "../../.env")

# Load toàn bộ biến từ file .env
env_vars = dotenv_values(dotenv_path)

# Đưa toàn bộ biến này vào os.environ (tự động cập nhật tất cả)
for key, value in env_vars.items():
    os.environ[key] = value

print(f"Loaded {len(env_vars)} environment variables from: {dotenv_path}")
