ircbot
======

Phenny modules for the helpful HSG bot in homestuck IRC channels.
Phenny is not the brightest IRC bot framework, but it does the job.

Modules here are:

* **notifier.py** : Checks a website every so often, utters an
  announcement with URL when the website updates.
* **hsg.py** : Uses the 4chan API to search through any
  subforum for threads starting with keywords. (commands: .hsg, .cgl )
* **verber.py** : Applies random actions using /me
* **reload.py** : The reload.py which ships with phenny kills the entire bot and reconnects it,
  which is a little inelegant. This just reloads the specified module.

Phenny comes with little-to-no documentation out of the box, so we wrote our own, see doc/
