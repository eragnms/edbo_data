Debugging
=========

Use the DAP debugger. Emacs is set up in the file .dir-locals.el.
Start the script with::

  python -Xfrozen_modules=off -m debugpy --listen 5678 --wait-for-client -m edbov_data.<module>

In Emacs::

  M x dap-breakpoint-add
  M x dap-debug
  M x dap-hydra
