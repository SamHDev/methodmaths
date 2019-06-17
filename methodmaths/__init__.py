import requests
import subprocess
import json
from urllib.parse import unquote

class LoginError(Exception):
   pass
class PaperLoadError(Exception):
   pass
class SessionWriteError(Exception):
   pass
class PaperError(Exception):
   pass


rq = """curl -sS 'https://www.methodmaths.com/gcse/passcheck.php' -H 'Pragma: no-cache' -H 'Origin: httppt-Encoding: gzip, deflate, br' -H 'Accept-Language: en-GB,en;q=0.9,en-US;q=0.8' -H 'User-Agent: Mozilla/5.0 (X11; CrOS x86_64 11151.113.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.127 Safari/537.36' -H 'Content-Type: application/x-www-form-urlencoded' -H 'Accept: */*' -H 'Cache-Control: no-cache' -H 'X-Requested-With: ShockwaveFlash/32.0.0.101' -H 'Cookie: __cfduid=d1d4e6ddfdfb7b5b217a999d76a9999771547555492' -H 'Connection: keep-alive' -H 'Referer: https://www.methodmaths.com/login.html' --data 'CENTRE={center}&PASS={password}&USER={username}' --compressed"""
    
def login(center,username,password):
   a = subprocess.Popen(rq.format(center=center,username=username,password=password),shell=True,stdout=subprocess.PIPE)
   a.wait()
   out = a.stdout.read().decode("UTF-8")
   d = {}
   for b in out.split("&"):
      d[b.split("=",1)[0]] = b.split("=",1)[1]
   if ("USERID0" not in d.keys()):
      raise LoginError("Details are not Correct")
   else:
      s = MethodMathsSession(center,username,password,d["USERID0"])
      return s
  
def parseString(text):
   data = {}
   for b in text.split("&"):
      data[b.split("=",1)[0]] = b.split("=",1)[1]
   return data
      
class MethodMathsSession():
   def __init__(self,center,username,password,userid):
      self.center = center
      self.username = username
      self.password = password
      self.userid = userid
      
      self.first_name = None
      self.last_name = None
      self.name = None
      self.school_name = None
      self.school_id = None
      self.account_type = None
      self.school_year = None
      self.school_group = None
      
      self._loadDataV3("June2012_1F")
      self.papers = []
      self.rawPaperData = self._loadResultsPageV7()
   
   def _loadDataV3(self,testname):
      r = requests.post("https://www.methodmaths.com/gcse/loadDataV3.php",data={"CENTRE":self.center,"USERID":self.userid,"TESTNAME":testname})
      d = parseString(r.text)
      
      self.first_name = d["FIRST0"]
      self.last_name = d["LAST0"]
      self.name = self.first_name + " " + self.last_name
      self.school_name = d["SCHOOLNAME0"]
      self.school_id = d["UPN0"]
      self.account_type = d["ACCOUNTTYPE0"]
      self.school_year = d["YEAR0"]
      self.school_group = d["GROUP0"]
      v = json.dumps(d,indent=4)
      f = open("out1.txt","w")
      f.write(v)
      f.close()
      
   def _loadResultsPageV7(self):
      
      self.papers = []
      
      r = requests.post("https://www.methodmaths.com/gcse/loadResultsPageDataV7.php",data={"CENTRE":self.center,"USERID":self.userid})
      d = parseString(r.text.replace("+","%20"))
      e = {}
      for k in d.keys():
         if ("46" in k) and ("146" not in k) :
            e[k.replace("46","")] = d[k]
      v =json.dumps(e,indent=4)
      f = open("out2.txt","w")
      f.write(v)
      f.close()
      
      paperIds = []
      for p in d.keys():
         if ("TITLES" in p):
            paperIds.append(int(p.replace("TITLES","")))
      for p in paperIds:
         self.papers.append(MethodMathsPaper(self,int(p),d))
   
   def reload(self):
      self.rawPaperData = self._loadResultsPageV7()
   
   def getPaper(self,term):
      for p in self.papers:
         if (str(p.paper_name).lower() == str(term).lower()):
            return p
         if (str(p.paper_id).lower() == str(term).lower()):
            return p
         if (str(p.paper_no).lower() == str(term).lower()):
            return p
      raise PaperError("Paper Not Found")
            
   def _writeRaw(self,testname,datastring,ansstring,throw=True):
      dt = {"CENTRE":self.center,"USERID":self.userid,"TESTNAME":testname,"DATASTRING":datastring,"ANSSTRING":ansstring}
      r = requests.post("https://www.methodmaths.com/gcse/saveData.php",data=dt)
      if ("writing=ok" not in r.text):
         if throw:
            raise SessionWriteError("Failed to Write to Endpoint")
         return False
      else:
         return True
      

class MethodMathsQuestion():
   def __init__(self,pap,qname,topic,maxmarks,cmarks,aws):
      self.paper = pap
      self.name = qname
      self.number = int(qname.split("Q",1)[1])
      self.id = str(pap.paper_id).strip() + "_" + str(int(qname.split("Q",1)[1])).strip()
      self.topic = topic
      self.marks_max = []
      self.marks_current = []
      self.answers = aws
      
      self.answers_trimed = []
      
      for a in self.answers:
         if (a != "") and (a != "0^0"):
            self.answers_trimed.append(a)
      
      self.mark_max = 0
      self.mark_current = 0
      for a in maxmarks:
         try:
            a = int(a)
         except:
            a = 0
         self.marks_max.append(a)
         self.mark_max = self.mark_max + a
      
      for a in cmarks:
         try:
            a = int(a)
         except:
            a = 0
         self.marks_current.append(a)
         self.mark_current = self.mark_current + a    
   
   def setAnswer(self,data,score):
      self.answers = data
      if (score != None):
         self.marks_currents = score
      else:
         self.marks_currents = self.marks_max
         
      for a in self.answers:
         if (a != "") and (a != "0^0"):
            self.answers_trimed.append(a)
      
   def _compileData(self):
      scoreData = "*".join(str(self.marks_current).replace("[","",1).replace("]","",1).split(","))
      ansData = "*".join(self.answers)
      return scoreData,ansData

class MethodMathsPaper():
   def __init__(self,sesh,number,data):
      
      self.session = sesh
      number = str(number)
      self.paper_name = data["TITLES"+number]
      #print(self.paper_name)
      
      self.paper_id = data["PAPERS"+number]
      self.paper_no = int(number)
      self.paper_board = data["BOARDS"+number]
      self.paper_length = int(data["NUMQUESTIONS"+number])
      self.mark_bounds_raw = data["BOUNDARIES"+number]
      self.mark_bounds = {}
      self.mark_max = 0
      self.mark_count = 0
      self.mark_max_raw = data["MARKDATA" + number]
      self.mark_count_raw = data["USERDATA" + number]
      
      self.qests_topic_raw = unquote(data["TOPICDATA"+number])
      
      self.raw_user_aws = unquote(data["USERRESPONSES"+number])
      
      self.questions = []
      
      
      for b in self.mark_bounds_raw.split("#"):
         self.mark_bounds[b.split("*")[1]] = b.split("*")[0]
         
      for b in self.mark_max_raw.split("#"):
         for a in b.split("*"):
            if (a!=""):
               self.mark_max = self.mark_max + int(a)
            
      for b in self.mark_count_raw.split("#"):
         for a in b.split("*"):
            if (a!=""):
               self.mark_count = self.mark_count + int(a)
      
      
      for i in range(0,self.paper_length):
         try:
            #print(self.paper_name + ": " + str(i))
            nam = self.paper_name + " Q" + str(i+1)
            topic = self.qests_topic_raw.split("#")[i].replace("+"," ").split("*")
            aws = self.raw_user_aws.split("#")[i].split("*")
            maxm = self.mark_max_raw.split("#")[i].split("*")
            curm = self.mark_count_raw.split("#")[i].split("*")
            a = MethodMathsQuestion(self,nam,topic,maxm,curm,aws)
            self.questions.append(a)
         except:
            pass
   
   def getGrade(self):
      lm = ""
      for mbk in self.mark_bounds.keys():
         mbv = self.mark_bounds[mbk]
      return lm
   
   def _compileData(self):
      ansList = []
      scoreList = []
      
      for q in self.questions:
         s ,a = q._compileData()
         scoreList.append(s)
         ansList.append(a)
      scoreData = "#".join(scoreList)
      ansData = "#".join(ansList)
      
      return scoreData, ansData
   
   def write(self):
      s,a = self._compileData()
      self.session._writeRaw(self.paper_id,s,a)
      

      
         
