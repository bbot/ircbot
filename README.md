ircbot
======

phenny modules for the helpful HSG bot in homestuck IRC channels.
phenny is not the brightest irc bot framework, but it does the job.

modules here are:

* **thanks.py** : a 'hello world' module.  ".thanks" -> "You're welcome."
* **notifier.py** : checks a website every so often, utters an
  announcement with url when the website updates.
* **crackship.py** : slightly more complicated example of a phenny module.
  Listens for '!ship' or '!ship name', and utters 'I ship name and name'
  from a list of names configured in the module
* **hsg.py** : *(depricated)* checks catalot.neet.tv/co/ for what should be the 
  4chan conversation thread currently discussingn Homestuck. 
* **tell_4chan_thread.py** : uses the 4chan API to search through any
  subforum for threads starting with keywords. (commands: !hsg, !cgl )

Please read phenny\_module\_howto.md and examine the existing modules
if you wish to make your own.

