"""Allow running as: python -m transmate"""
from .cli import TransMateCLI

def main():
	TransMateCLI().run()

if __name__ == "__main__":
	main()
