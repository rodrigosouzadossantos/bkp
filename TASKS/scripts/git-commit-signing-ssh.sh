#!/bin/bash

# GitHub SSH Key Setup Script (for commit signing) [git-commit-signing-ssh.sh]

# This script automates the process of setting up an SSH key for signing git
# commits and configuring git to use that key for signing. It is designed to be
# run in a git repository, and it will modify the local git configuration to use
# the generated SSH key for signing commits. The script also provides
# instructions for adding the public key to GitHub, which is necessary for
# GitHub to recognize the signatures on commits made with that key.

# Function to check if we're in a git repositor
# This is important because the script modifies local git configuration, and it
# should only be run in a git repository to avoid confusion.
# 
# If the check fails, the script will exit with an error message.
# 
# This ensures that users don't accidentally run the script in a non-git
# directory, which could lead to unexpected behavior or confusion about where
# the SSH key is being used.
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo "Error: Not a git repository"
        exit 1
    fi
}

# Function to generate SSH key
#
# This function generates an SSH key using the ed25519 algorithm, which is
# recommended for its security and performance benefits. The key is saved to
# ~/.ssh/git_signing_key, and the public key is saved to
# ~/.ssh/git_signing_key.pub.
#
# The function also checks if a key already exists at the specified location.
# If it does, it prompts the user to confirm whether they want to overwrite the
# existing key. This is a safety measure to prevent accidental loss of an
# existing key that may be in use.
generate_ssh_key() {
    local key_comment=$1
    
    if [ -f ~/.ssh/git_signing_key ]; then
        echo "Warning: SSH key git_signing_key already exists"
        read -p "Do you want to overwrite it? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Aborting..."
            exit 1
        fi
    fi
    
    ssh-keygen -t ed25519 -C "$key_comment" -f ~/.ssh/git_signing_key -N ""
    
    # Set correct permissions
    chmod 600 ~/.ssh/git_signing_key
    chmod 644 ~/.ssh/git_signing_key.pub
}

# Function to configure git
#
# This function sets the local git configuration to use the generated SSH key
# for signing commits. It configures git to use the SSH key format for GPG
# signing, sets the signing key to the public key we generated, and enables
# automatic signing of commits.
#
# This configuration is local to the repository where the script is run, so it
# won't affect other repositories or global git settings. This allows users to
# have different signing keys for different repositories if they choose to do so.
#
configure_git(  ) {
    echo -e "\nSetting local git configuration to use the generated signing key.."
    
    git config gpg.format ssh
    git config user.signingkey "~/.ssh/git_signing_key.pub"
    git config commit.gpgsign true
    
    echo -e "Git configuration complete!\n\n"
}

# Function to display public Key
#
# This function displays the generated public SSH key to the user, along with
# instructions on how to add it to GitHub. It provides a clear message
# indicating that this is the public key that needs to be added to GitHub, and
# it includes a link to the GitHub settings page where the key can be added.
display_key() {
    echo "Here's your public key to add to GitHub:"
    echo "----------------------------------------"
    cat ~/.ssh/git_signing_key.pub
    echo "----------------------------------------"
    echo "Add this key to GitHub by visiting: https://github.com/settings/keys"
    echo "Make sure to choose the key type as 'Signing Key' when adding it. Once
          done, your setup is complete."
}

# Main script
#
# The main function orchestrates the execution of the script. It first checks if
# the user is in a git repository, then prompts the user for a comment to
# associate with the SSH key. It proceeds to generate the SSH key, configure git
# to use it for signing commits, and finally displays the public key with
# instructions for adding it to GitHub.
main() {
    check_git_repo
    
    # Get user input
    read -p "Enter a comment for your key (e.g., your name, email, etc): " \
      key_comment
    
    # Setup steps
    generate_ssh_key "$key_comment"
    configure_git
    display_key
}

# Run main function
#
# This line calls the main function to execute the script. It ensures that all
# then defined functions are executed in the correct order, starting with
# checking if we're in a git repository, then generating the SSH key,
# configuring git, and finally displaying the public key for GitHub.
main
