from app.streamlit_app import main
os.environ["STREAMLIT_SERVER_PORT"] = "7860"
os.environ["STREAMLIT_SERVER_ADDRESS"] = "0.0.0.0"

# Launch your existing Streamlit app
subprocess.run([
    "streamlit", "run", "app/streamlit_app.py",
    "--server.port", "7860",
    "--server.address", "0.0.0.0"
])
if __name__ == "__main__":
    main()
