#!/bin/bash

# This script starts the ssh-agent and opens a new Bash shell session as a child
# process of the ssh-agent program. It also checks if the SSH agent is already
# running before starting it.
#
# The ssh-agent is a program that holds your private SSH keys in memory and
# provides them to SSH clients when needed. This allows you to use your SSH keys
# for authentication without having to enter your passphrase every time you
# connect to a remote server.
#
# When you run this script, it will start the ssh-agent if it is not already
# running and then open a new Bash shell session where you can add your SSH keys
# using the ssh-add command. The SSH agent will keep your keys in memory,
# allowing you to use them for authentication in future SSH connections without
# having to enter your passphrase again.
#
# To use this script, save it to a file (e.g., ssh-agent.sh), make it executable
# with chmod +x ssh-agent.sh, and then run it with ./ssh-agent.sh. It will start
# the ssh-agent and open a new Bash shell session where you can add your SSH
# keys using ssh-add.
#
# Note: This script assumes that you have the ssh-agent program installed on
# your system. If you don't have it, you may need to install it using your
# package manager (e.g., apt-get install openssh-client on Debian-based systems).
#
# The script first checks if the SSH_AUTH_SOCK environment variable is set,
# which indicates that the SSH agent is already running. If it is not set, it
# starts the SSH agent using eval "$(ssh-agent -s)". Finally, it opens a new
# Bash shell session as a child process of the ssh-agent program using
# ssh-agent bash.
#
# This allows you to use the SSH agent in the new shell session, and any SSH
# keys added to the agent will be available in that session. You can add your
# SSH keys using the ssh-add command, and they will be stored in the SSH agent
# for use in future SSH connections.
#
# Remember to add your SSH keys to the agent using ssh-add after starting the
# agent, and you can check the list of added keys with ssh-add -l. The SSH
# agent will keep your keys in memory, allowing you to use them for
# authentication without having to enter your passphrase every time you
# connect to a remote server.
#
# Overall, this script provides a convenient way to start the SSH agent and
# manage your SSH keys in a new Bash shell session.

ssh-agent bash

# Check if the SSH agent is already running
if [ -z "$SSH_AUTH_SOCK" ]; then
    # Start the SSH agent
    eval "$(ssh-agent -s)"
else
    echo "SSH agent is already running."
fi

ssh-agent -l
