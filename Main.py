from bs4 import BeautifulSoup
import requests
import random
import time
import json
import re
import os
import lz4.frame

from colorama import init, Fore, Back, Style

init(convert=True)

DiscordTagRegex = r"[^\r\n\t\f\v\0-\x1F\x7F]{2,32}#[0-9]{4}"

def AppendListToListNoRepeat(ListTo, ListFrom):
	for Item in ListFrom:
		if not Item in ListTo:
			ListTo.append(Item)

def WebScrapSteamFriendsPage(Data, BuildOn):
	Soup = BeautifulSoup(Data, "html.parser")
	Friends = []
	for Friend in Soup.find_all("a", "selectable_overlay"):
		Friends.append(Friend["href"])
	BuildOn["Friends"] = Friends

def WebScrapSteamProfilePage(Data):
	Soup = BeautifulSoup(Data, "html.parser")
	Result = {}

	Result["UserName"] = Soup.find_all("span", "actual_persona_name")[0].string
	
	About = Soup.find_all("div", "profile_summary")
	Result["About"] = (len(About) > 0 and About[0].text) or ""

	FriendsURL = Soup.find("a", href=re.compile(r"\/friends\/"))
	if FriendsURL:
		WebScrapSteamFriendsPage(requests.get(FriendsURL["href"]).content, Result)
	
	return Result

def LoadAutoSave():
	if os.path.isfile("AutoSave.json"):
		print(Fore.CYAN + "Loading State...", end='')
		with open("AutoSave.json", "rb") as File:
			Loaded = json.loads(lz4.frame.decompress(File.read()).decode(encoding="ascii"))
			File.close()
			print(" Done" + Style.RESET_ALL)
			return Loaded
	print(Fore.YELLOW + "Save File Not Found, No State Will Be Loaded." + Style.RESET_ALL)

def SaveAutoSave(State):
	print(Fore.CYAN + "Saving State...", end='')
	with open("AutoSave.json", "wb") as File:
		Uncompressed = json.dumps(State)
		Compressed = lz4.frame.compress(Uncompressed.encode())

		print(" Compression: {0:.2f}% Writing...".format((1 - (len(Compressed) / len(Uncompressed))) * 100), end='')
		File.write(Compressed)
		File.close()
	print(" Done" + Style.RESET_ALL)


def main():
	AutoSave = LoadAutoSave() or {}

	Done = []
	if "Done" in AutoSave:
		Done = AutoSave["Done"]

	Todo = ["https://steamcommunity.com/id/rafa_br34"]
	if "Todo" in AutoSave:
		Todo = AutoSave["Todo"]

	Discords = open("Discords.txt", "ab")

	Stop = False
	while not Stop:
		try:
			while True:
				URL = Todo.pop(random.randint(0, len(Todo) - 1))
				if URL in Done:
					continue
				else:
					Done.append(URL)

				Result = WebScrapSteamProfilePage(requests.get(URL).content)
				if "Friends" in Result:
					Todo += Result["Friends"]
					#AppendListToListNoRepeat(Todo, Result["Friends"])

				if len(Result["About"]) > 0 and not ("No information given." in Result["About"]):
					print(Fore.YELLOW + "{}/{}".format(len(Done), len(Todo)) + Style.RESET_ALL + " \"{}\" {}: {}".format(URL, Result["UserName"], Result["About"]))
				else:
					print(Fore.MAGENTA + "{}/{}*\t\t\t\t".format(len(Done), len(Todo)) + Style.RESET_ALL, end='\r')
				
				for Tag in re.findall(DiscordTagRegex, Result["About"]):
					print(Fore.RED + str(Tag), end="")
					Discords.write((URL + " :->: " + Tag + u"\n").encode("utf-8"))
					print(Style.RESET_ALL)
		except KeyboardInterrupt as E:
			print(Fore.CYAN)
			print("\nKeyboardInterrupt, Stopping...")
			print("Final Count: {}/{}".format(len(Done), len(Todo)))
			Stop = True

		except Exception as E:
			print("Unknown Exception: ", E, "\n--------------------------------\nRESTARTING SOON\n--------------------------------")
		SaveAutoSave({"Done": Done, "Todo": Todo})
		Discords.close()
		print("AutoSave Saved, Discords.txt Closed.")
		
		if not Stop:
			Discords = open("Discords.txt", "ab")
			print("Files Saved/Reopened, Restarting Loop In 5 Seconds...")
			time.sleep(5)
	
	print("Quitting...")
	print(Style.RESET_ALL)

	

if __name__ == "__main__":
	main()