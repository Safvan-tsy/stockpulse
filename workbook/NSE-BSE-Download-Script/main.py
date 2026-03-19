# ----
import requests
import zipfile
import io
import os

Link_1 = "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{0}_F_0000.csv.zip"
Link_2 = "https://nsearchives.nseindia.com/archives/equities/mto/MTO_{0}.DAT"
Link_3 = "https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{0}_F_0000.CSV"
Link_4 = "https://www.bseindia.com/BSEDATA/gross/{0}/SCBSEALL{2}{1}.zip"

Year = str(input("Enter the Year (YYYY format): "))
Month = str(input("Enter the Month (MM format): "))
Day = str(input("Enter the Day (DD format): "))

Date_1 = "{2}{1}{0}".format(Day, Month, Year)
Date_2 = "{0}{1}{2}".format(Day, Month, Year)

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

# ----


# Link 1
try:
    response = requests.get(Link_1.format(Date_1), headers=headers)
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        zip_file.extractall("data")
    print("[+] File Downloaded Successfully (Link 1)")
except Exception as Error:
    print("[-] (Link 1) - ", Error)

# Link 2
File_Name = "MTO_{0}.csv".format(Date_2)

try:
    response = requests.get(Link_2.format(Date_2), headers=headers)
    if response.status_code == 200:
        with open("data\\tmp.dat", "wb") as f:
            f.write(response.content)
        print("[+] DAT file downloaded successfully! (Link 2)")
        
        with open("data\\tmp.dat", "r") as f:
            Lines = f.readlines()
            
        New_Date = Lines[2].split(" ")[2].strip("<").strip(">,Settlement")
        Lines = Lines[4:]
        New_Lines = ["{0},{1}".format(New_Date, i) for i in Lines]
        
        with open("data\\{0}".format(File_Name), "w") as f:
            f.writelines(New_Lines)
        
        print("[+] {0} file has been created! (Link 2)".format(File_Name))
        os.remove("data\\tmp.dat")
                
    else:
        print(f"[-] Error: {response.status_code} (Link 2)")

except Exception as Error:
    print("[-] (Link 2) - ", Error)

# Link 3
File_Name = "BhavCopy_BSE_CM_0_0_0_{0}_F_0000.csv".format(Date_1)
try:
    response = requests.get(Link_3.format(Date_1), headers=headers)
    if response.status_code == 200:
        with open("data\\{0}".format(File_Name), 'wb') as f:
            f.write(response.content)
        print("[+] File Downloaded Successfully (Link 3)")
    else:
        print(f"[-] Error: {response.status_code} (Link 3)")
except Exception as Error:
    print("[-] (Link 3) - ", Error)

# Link 4
try:
    response = requests.get(Link_4.format(Year, Month, Day), headers=headers)
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        zip_file.extractall("data")
    print("[+] File Downloaded Successfully (Link 4)")
except Exception as Error:
    print("[-] (Link 4) - ", Error)