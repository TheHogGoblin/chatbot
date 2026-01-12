from flask import Flask,render_template,url_for,request,redirect
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import sqlite3,os,datetime
app=Flask(__name__)
#configuration
load_dotenv()
llm=ChatGoogleGenerativeAI(model='gemini-2.5-flash',google_api_key=os.getenv("GOOGLE_API_KEY"))
DB_FILE="chatbot.db"

#db setup
def init_db():
    conn=sqlite3.connect(DB_FILE)
    c=conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chats(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   title TEXT,
                   created_at TEXT

             )''') 
    c.execute('''CREATE TABLE IF NOT EXISTS messages(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    sender TEXT,
                    text TEXT,
                    created_at TEXT,
                    FOREIGN KEY(chat_id) REFERENCES chats(id)
             
   

                 )''')
    conn.commit()
    conn.close()
init_db()    

#ROUTES SETUP
@app.route('/')
def home():
    conn=sqlite3.connect(DB_FILE)
    c=conn.cursor()
    c.execute("SELECT id ,title FROM chats ORDER BY created_at DESC")
    chats=c.fetchall()
    conn.close()

    if chats:
        return redirect(url_for("view_chat", chat_id=chats[0][0]))
    else:
        return redirect(url_for("new_chat"))




@app.route("/chat/<int:chat_id>")
def view_chat(chat_id):
    conn=sqlite3.connect(DB_FILE)
    c=conn.cursor()
    c.execute("SELECT id,title FROM chats ORDER BY created_at DESC")
    all_chats=c.fetchall()
    c.execute("SELECT sender,text FROM messages WHERE chat_id=? ORDER BY created_at ASC",(chat_id,))
    chat_history=[{'sender':row[0],'text':row[1]}for row in c.fetchall()]
    conn.close()

    return render_template("index.html",chats=all_chats,chat_history=chat_history,current_chat=chat_id)

@app.route("/new_chat")
def new_chat():
    conn=sqlite3.connect(DB_FILE)
    c=conn.cursor()
    now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO chats (title,created_at) VALUES (?,?)",(F"Chat {now}",now))
    chat_id=c.lastrowid

    #ADD INITIAL AI WELCOME MESSAGE
    c.execute("INSERT INTO messages (chat_id,sender,text,created_at) VALUES (?,?,?,?)",
              (chat_id,"ai","Hello! How can I help you today?",now))
    conn.commit()
    conn.close()
    return redirect(url_for("view_chat",chat_id=chat_id))

@app.route("/send/<int:chat_id>",methods=['POST'])
def send_message(chat_id):
    user_message=request.form.get('message',' ').strip()
    now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    #store user message in db
    with sqlite3.connect(DB_FILE,timeout=10) as conn:
        c=conn.cursor()
        c.execute("INSERT INTO messages(chat_id, sender,text, created_at) VALUES (?,?,?,?)", (chat_id,"user",user_message,now))
        conn.commit()
        
        
    # call llm
    import markdown
    prompt=f"You are an intelligent bot and answer this query {user_message}"
    

    ai_reply_raw = llm.invoke(prompt).content.strip()
    ai_reply = markdown.markdown(ai_reply_raw)

    # store ai response in db
    with sqlite3.connect(DB_FILE,timeout=10) as conn:
        c=conn.cursor()
        c.execute("INSERT INTO messages(chat_id, sender,text, created_at) VALUES (?,?,?,?)", (chat_id,"ai",ai_reply,now))

        conn.commit()
        return redirect(url_for("view_chat",chat_id=chat_id))
#PYTHON MAIN
if __name__=="__main__":
    app.run(debug=True)