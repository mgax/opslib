FROM alpine
RUN apk add openssh-server python3 sudo
RUN echo "opslib ALL=(ALL:ALL) NOPASSWD: ALL" > /etc/sudoers.d/opslib
RUN sed -ie 's/#Port 22/Port 22/g' /etc/ssh/sshd_config
RUN adduser -D opslib
RUN passwd -u opslib
RUN mkdir /home/opslib/.ssh
COPY ssh_host_ed25519_key ssh_host_ed25519_key.pub /etc/ssh/
COPY id_ed25519.pub /home/opslib/.ssh/authorized_keys
RUN chmod 600 /etc/ssh/ssh_host_ed25519_key
RUN chown opslib: /home/opslib/.ssh /home/opslib/.ssh/*
CMD /usr/sbin/sshd -D
