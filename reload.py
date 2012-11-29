"""
reload.py - Phenny Module Reloader Module
  http://inamidst.com/phenny/
first version: (c) 2008, Sean B. Palmer
  under the Eiffel Forum License 2.
this version: Mozai is trying to bang this
  into shape so it will be more useful than
  just a deadman switch you kick with a boot.
"""

import sys, os, os.path, time, imp

def f_reload(phenny, cmd_in):
  " Reloads a module, for use by admins only. "

  if not cmd_in.admin:
    # don't even return a warning message
    return

  def reply(mesg) :
    " because phenny.wrapped().reply() is broken "
    phenny.msg(cmd_in.nick, mesg)

  def _list_registered_modules(bot) :
    """ ugh, this should ALREADY be a feature of bot.Phenny
        but I can't touch the core classes in this implementation.
    """
    home = os.path.abspath(os.getcwd()) 
    # os.getcwd() is not my idea; that's what's in bot.py
    modulepaths = [ os.path.join(home,'modules') ]
    if hasattr(bot.config,'extra'):
      for i in bot.config.extra :
        i = os.path.abspath(i)
        if os.path.isfile(i):
          modulepaths.append(os.path.dirname(i))
        elif os.path.isdir(i):
          modulepaths.append(i)
        else:
          pass
    modulelist = list()
    for modulename in sys.modules :
      if modulename.startswith('_'):
        continue
      if hasattr(sys.modules[modulename], '__file__'):
        for path in modulepaths :
          if sys.modules[modulename].__file__.startswith(path) :
            modulelist.append(modulename)
            continue
    return modulelist

  param = cmd_in.group(2)  # group(1) == 'reload'
  if ' ' in param :
    modules_desired = param.split()
  else:
    modules_desired = [ param ]

  if '*' in modules_desired :
    phenny.variables = None
    phenny.commands = None
    phenny.setup()
    modules = _list_registered_modules(phenny.bot)
    modules.sort()
    reply('reloaded all modules ' + repr(modules))
    return

  for name in modules_desired :
    if not sys.modules.has_key(name) :
      reply('%s: no such module!' % name)
      continue

    path = sys.modules[name].__file__
    if path.endswith('.pyc') or path.endswith('.pyo') :
      path = path[:-1]
    if not os.path.isfile(path):
      reply('Found %s, but not the source file' % name)
      continue

    module = imp.load_source(name, path)
    sys.modules[name] = module
    if hasattr(module, 'setup'):
      module.setup(phenny)

    mtime = os.path.getmtime(module.__file__)
    modified = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(mtime))

    phenny.register(vars(module))
    phenny.bind_commands()

    reply('%r (mtime: %s)' % (module, modified))

f_reload.name = 'reload'
f_reload.example = '.reload * or .reload module_name1 module_name2 ...'
f_reload.rule = ('$nick', ['reload'], r'(.*)')
f_reload.commands = (['reload'])
f_reload.priority = 'low'
f_reload.thread = False

