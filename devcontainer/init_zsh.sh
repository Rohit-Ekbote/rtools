# Install Oh My Zsh non-interactively
curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh | zsh

#RUN apk add git-extras
source $ZDOTDIR/.zshrc
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-$ZSH/custom}/plugins/zsh-syntax-highlighting
git clone https://github.com/zsh-users/zsh-autosuggestions.git ${ZSH_CUSTOM:-$ZSH/custom}/plugins/zsh-autosuggestions
git clone https://github.com/zsh-users/zsh-completions.git ${ZSH_CUSTOM:-$ZSH/custom}/plugins/zsh-completions
git clone https://github.com/zsh-users/zsh-history-substring-search.git ${ZSH_CUSTOM:-$ZSH/custom}/plugins/zsh-history-substring-search
#git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM:-$ZSH/custom}/themes/powerlevel10k 
#ADD ./rscripts/p10k.zsh $RUNDEV_HOME/.config/zsh/.p10k.zsh

#omz theme set powerlevel10k/powerlevel10k
#omz theme set agnoster
#omz plugin enable git
omz plugin enable git-extras
omz plugin enable zsh-syntax-highlighting
omz plugin enable zsh-autosuggestions
omz plugin enable zsh-completions
omz plugin enable zsh-history-substring-search
omz plugin enable common-aliases
omz plugin enable kubectl
omz plugin enable aws
omz plugin enable docker
omz plugin enable fluxcd
omz plugin enable gcloud
#omz plugin enable k9s


