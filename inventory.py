from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import telegram
import asyncio, json
import time, datetime
import re
import socket

def tesla_inven(model):
	options = Options()

	hostname = socket.gethostname()
	if hostname == 'jungui-MacBookAir.local':
		# options.add_argument("headless") #크롬창이 뜨지 않고 백그라운드로 동작됨
		pass
	else:
		options.add_argument("headless") #크롬창이 뜨지 않고 백그라운드로 동작됨

	# 아래 옵션 두줄 추가(NAS docker 에서 실행시 필요, memory 부족해서)
	options.add_argument('--no-sandbox')
	options.add_argument('--disable-dev-shm-usage')

	# headless로 동작할때 element를 못찾으면 아래 두줄 추가 (창크기가 작아서 못찾을수 있음)
	options.add_argument("start-maximized")
	# options.add_argument("window-size=1920,1080")
	# options.add_argument("window-size=1920,2160")	# 창크기가 작아서 전체 내용이 표시되지 않아서 크게 키움
	options.add_argument("window-size=1920,3000")	# 창크기가 작아서 전체 내용이 표시되지 않아서 크게 키움
	# options.add_argument("disable-gpu")
	# options.add_argument("lang=ko_KR")

	# 아래는 headless 크롤링을 막아놓은곳에 필요 (user agent에 HeadlessChrome 이 표시되는걸 방지)
	options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')

	# config.json 파일처리 ----------------
	with open('config.json','r') as f:
		config = json.load(f)
	url = config[model]['URL']
	list_onoff = config[model]['LIST']
	# ------------------------------------

	driver = webdriver.Chrome(options=options)

	def extract_numbers_as_string(string):	# string에서 숫자만 뽑아내는 함수
		pattern = r'\d+'  # Match one or more digits
		numbers = re.findall(pattern, string)
		result = ''.join(numbers)
		return result
	
	# 인벤토리 페이지 접속
	check_count = 0
	while True:
		driver.get(url)
		time.sleep(3)
		#driver.maximize_window()
		action = ActionChains(driver)
		try:
			cars = driver.find_elements(By.CLASS_NAME, "result.card")
			length = len(cars)
		except:
			length = 0
		if length > 0:	# inventory 차량을 1대이상 발견한 경우에는 stop, 0 대이면 재시도
			break
		check_count = check_count + 1
		if check_count > 2:	# 재시도는 3회까지만 하고, pass
			break
	
	# result = f"<{model}> {length}대\n"
	result = f"[<{model}>]({url}?referral=jonghoon77925) _{length}대_\n"

	""" telegram bot Markdown syntax
	*bold text*
	_italic text_
	[inline URL](http://www.example.com/)
	[inline mention of a user](tg://user?id=123456789)
	`inline fixed-width code`
	```block_language
	pre-formatted fixed-width code block
	```
	"""
	if list_onoff == "ON":
		for car in cars:
			year_model = car.find_element(By.CLASS_NAME, "result-basic-info").find_element(By.CLASS_NAME, "tds-text--h4").text
			year = extract_numbers_as_string(year_model)
			model = car.find_element(By.CLASS_NAME, "result-basic-info").find_element(By.CLASS_NAME, "tds-text_color--10").text.replace("듀얼 모터 상시 사륜구동(AWD)","(AWD)")
			price = car.find_element(By.CLASS_NAME, "result-purchase-price.tds-text--h4").text
			detail = (
				car.find_element(By.CLASS_NAME, "result-regular-features.tds-list.tds-list--unordered").text
				.replace("\n",", ")
				.replace(" 아라크니드 휠","")
				.replace(" 템페스트 휠","")
				.replace(" 터빈 휠","")
				.replace(" 사이버스트림 휠","")
				.replace(" 프리미엄 인테리어와 카본 파이버 데코","")
				.replace(" 프리미엄 인테리어와 에보니 데코","")
				.replace(" 프리미엄 인테리어와 월넛 데코","")
				.replace(" Multi-Coat","")
				.replace("요크 스티어링 휠","요크")
				.replace("스티어링 휠","원형")
			)
			# print(f"{price} : {year} {model} {detail}")
			result = f"{result} *{price}* : `{year} {model}` {detail}\n"
		
		
	driver.quit()
	return(result)


# telegram 메세지 발송함수
async def tele_push(content): #텔레그램 발송용 함수
	# config.json 파일처리 ----------------
	with open('config.json','r') as f:
		config = json.load(f)
	token = config['TELEGRAM']['TOKEN']
	chat_id = config['TELEGRAM']['CHAT-ID']
	# ------------------------------------
	current_time = datetime.datetime.now()
	formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
	bot = telegram.Bot(token = token)
	# await bot.send_message(chat_id, formatted_time + "\n" + content)
	await bot.send_message(chat_id, formatted_time + "\n" + content, parse_mode = 'Markdown', disable_web_page_preview=True)

# tesla_inven 함수 실행
inventory1 = tesla_inven('MODEL_S')
inventory2 = tesla_inven('MODEL_X')

# print(inventory1)
# print(inventory2)
msg_content = inventory1 + "\n" + inventory2
# print(msg_content)

with open('inven.txt','r') as file:
	file_content = file.read()

if file_content == msg_content:	# 변경이 없으면
	pass
else:	# 변경이 있을때 현재 인벤토리 내용을 파일로 저장
	file_path = "inven.txt"
	file = open(file_path, 'w')
	file.write(msg_content)
	file.close
	asyncio.run(tele_push(msg_content)) #텔레그램 발송 (asyncio를 이용해야 함)
