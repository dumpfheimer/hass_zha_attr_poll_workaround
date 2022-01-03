1. be aware that this is a hacky workaround and is not well tested

2. install requirements
pip install -r requirements.txt

3. copy the example config
cp config.yaml.example config.yaml

4. edit your config
4.1 configure your websocket URL
4.2 obtain and configure your long lived api token

5. go!
python3 PollAttributes.py

6. check for errors / check if the values are update in HA
