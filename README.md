# Kubeturbo

An Ansible role to update the ConfigMap and docker image tag used for the deployment of [kubeturbo](https://github.com/turbonomic/kubeturbo).

An array of image pull secrets can also be specified. The role will only add, or update image pull secrets, and can not remove the image pull secrets from the deployment.

If image pull secrets are specified, the current settings for `imagePullSecrets` on the deployment will be overwritten. As such, *all* desired secret names must be supplied.

## Requirements

This role requires a python3 interpreter, and the python modules for the Ansible [k8s](https://docs.ansible.com/ansible/latest/modules/k8s_module.html) and [k8s_auth](https://docs.ansible.com/ansible/latest/modules/k8s_auth_module.html) modules. Namely;

* openshift >= 0.6
* PyYAML >= 3.11
* urllib3
* requests
* requests-oauthlib

Additionally, the k8s module must be authenticated with the Kubernetes cluster you intend to operate against, which needs to be configured before applying the role.

There are four primary ways that the module can authenticate with kubernetes.

1. With a kubeconfig file and context
2. With basic authentication using a username and password
3. With an API access token
4. With a Client SSL Certificate and Private Key

You can acquire an API access token either from a service account, or by logging into an OpenShift cluster using oAuth.

To (re)use the token for the kubeturbo service account, you can extract them thusly if you are a cluster or namespace admin.

```
#!/usr/bin/env bash
NAMESPACE=turbo
SECRET_NAME=$(kubectl -n $NAMESPACE get sa turbo-user -o json | jq -r '.secrets[0].name')
kubectl -n $NAMESPACE get secret $SECRET_NAME -o json | jq -r '.data["token"] | @base64d' > token
# Note for OpenShift this is "service-ca.crt"
kubectl -n $NAMESPACE get secret $SECRET_NAME -o json | jq -r '.data["ca.crt"] | @base64d' > ca.pem
```

Also see [Example Playbooks](#example-playbooks).

## Role Variables

| Variable | Description | Required | Default Value |
|:---------|:------------|:---------|:--------------|
|kubeturbo_server_version|The version of the Turbonomic server kubeturbo will connect to, stored in the configmap.|true|N/A|
|kubeturbo_image|The full tag of the kubeturbo docker image to use.|true|N/A|
|kubeturbo_namespace|The namespace of the kubeturbo deployment|false|turbo|
|kubeturbo_configmap_name|The name of the kubeturbo configmap|false|turbo-config|
|kubeturbo_hanodeconfig|An array of Kubernetes node roles to consider for HA|false|N/A|
|kubeturbo_deployment_name|The name of the kubeturbo deployment|false|kubeturbo|
|kubeturbo_pull_secrets|An array of one or many secret names to be used by the deployment when pulling the kubeturbo image|false|N/A|
|k8s_host|The hostname of the Kubernetes cluster|false|N/A|
|k8s_api_key|A Kubernetes bearer token|false|N/A|

## Example Playbooks

### With a kubeconfig file

```
- name: Kubeconfig Auth - Single
  hosts: all
  vars:
    kubeturbo_server_version: "7.22"
    kubeturbo_image: turbonomic/kubeturbo:7.22.3
  module_defaults:
    group/k8s:
      kubeconfig: /opt/turbonomic/.kube/config
  roles:
    - role: kubeturbo
```

### With basic authentication

```
- name: Basic Auth - Single
  hosts: all
  vars:
    kubeturbo_server_version: "7.22"
    kubeturbo_image: turbonomic/kubeturbo:7.22.3
  module_defaults:
    group/k8s:
      username: "{{ k8s_username }}"
      password: "{{ k8s_username }}"
      ca_cert: /tmp/ca.pem
  roles:
    - role: kubeturbo
      k8s_host: "https://{{ ansible_host }}"
```

### With Service Account API token authentication

```
- name: Service Account API Auth - Single
  hosts: all
  vars:
    kubeturbo_server_version: "7.22"
    kubeturbo_image: turbonomic/kubeturbo:7.22.3
  module_defaults:
    group/k8s:
      api_key: "{{ k8s_api_key }}"
      ca_cert: /tmp/ca.pem
  pre_tasks:
    - name: Copy the ca to temp
      content: "{{ k8s_ca_pem }}"
      dest: /tmp/ca.pem
  roles:
    - role: kubeturbo
      k8s_host: "https://{{ ansible_host }}"
```

### With OpenShift API token authentication

```
- name: OpenShift API Auth - Single
  hosts: all
  vars:
    kubeturbo_server_version: "7.22"
    kubeturbo_image: turbonomic/kubeturbo:7.22.3
  module_defaults:
    group/k8s:
      ca_cert: /tmp/ca.pem
  pre_tasks:
    - name: Copy the ca to temp
      content: "{{ k8s_ca_pem }}"
      dest: /tmp/ca.pem
    - name: Login to OpenShift
      k8s_auth:
        username: "{{ oc_username }}"
        password: "{{ oc_password }}"
      register: k8s_auth_results
  post_tasks:
    - name: Logout of OpenShift
      when: k8s_auth_results.k8s_auth.api_key is defined
      k8s_auth:
        state: absent
        api_key: "{{ k8s_auth_results.k8s_auth.api_key }}"
  roles:
    - role: kubeturbo
      k8s_host: "https://{{ ansible_host }}"
      k8s_api_key: "{{ k8s_auth_results.k8s_auth.api_key }}"
```

### With SSL Client Certificate and Private Key

```
- name: SSL Auth - Single
  hosts: all
  vars:
    kubeturbo_server_version: "7.22"
    kubeturbo_image: turbonomic/kubeturbo:7.22.3
  module_defaults:
    group/k8s:
      client_cert: /tmp/client.crt
      client_key: /tmp/client.pem
      ca_cert: /tmp/ca.pem
  pre_tasks:
    - name: Copy the client cert to temp
      content: "{{ k8s_client_cert }}"
      dest: /tmp/client.crt
    - name: Copy the client key to temp
      content: "{{ k8s_client_key }}"
      dest: /tmp/client.pem
    - name: Copy the ca to temp
      content: "{{ k8s_ca_pem }}"
      dest: /tmp/ca.pem
  roles:
    - role: kubeturbo
      k8s_host: "https://{{ ansible_host }}"
```

### With a kubeconfig file and two instances of kubeturbo

```
- name: Kubeconfig Auth - Multiple Kubeturbo
  hosts: all
  vars:
    kubeturbo_prod_server_version: "7.22"
    kubeturbo_prod_image: turbonomic/kubeturbo:7.22.3

    kubeturbo_dev_server_version: "7.22"
    kubeturbo_dev_image: turbonomic/kubeturbo:7.22.4
    kubeturbo_dev_namespace: turbo-dev
  module_defaults:
    group/k8s:
      kubeconfig: /opt/turbonomic/.kube/config
  roles:
    # Update the kubeturbo connected to the production instance of Turbonomic
    - role: kubeturbo
      kubeturbo_server_version: "{{ kubeturbo_prod_server_version }}"
      kubeturbo_image: "{{ kubeturbo_prod_image }}"

    # Update the kubeturbo connected to the development instance of Turbonomic
    - role: kubeturbo
      kubeturbo_server_version: "{{ kubeturbo_dev_server_version }}"
      kubeturbo_image: "{{ kubeturbo_dev_image }}"
      kubeturbo_namespace: "{{ kubeturbo_dev_namespace }}"
```

### When prerequisites are not installed

```
- name: Kubeconfig Auth - Prereq
  hosts: all
  vars:
    kubeturbo_server_version: "7.22"
    kubeturbo_image: turbonomic/kubeturbo:7.22.3
    virtualenv_dir: /opt/deploy
  module_defaults:
    group/k8s:
      kubeconfig: /opt/turbonomic/.kube/config
  pre_tasks:
    - name: "Setup Dependencies"
      block:
      - name: "Create deployment folder"
        file: path={{ virtualenv_dir }} state=directory mode=0755

      - name: "Install Dependencies Debian"
        become: true
        package:
          name: "{{ item }}"
          state: present
        loop:
          - python3-virtualenv
          - libssl-dev
        when: ansible_facts['os_family'] == 'Debian'

      - name: "Install Dependencies RHEL"
        become: true
        package:
          name: "{{ item }}"
          state: present
        loop:
          - python3-virtualenv
          - openssl-devel
        when: ansible_facts['os_family'] == 'RedHat'

      - name: "Install python libraries"
        pip:
          name:
            - pip
            - openshift
            - pyyaml
          state: latest
          virtualenv: "{{ virtualenv_dir }}"
          virtualenv_site_packages: yes

      - name: "Tell subsequent tasks to use our deploy virtualenv"
        set_fact:
          ansible_python_interpreter: "{{ virtualenv_dir }}/bin/python3"
  roles:
    - role: kubeturbo
```
