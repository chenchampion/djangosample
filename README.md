A sample project for django reset framework

搭建环境:
1. 创建开发虚拟环境：
	1). sudo easy_install virtualenv
	2). virtualenv ~/myvirtualenv
	3). source ~/myvirtualenv/bin/activate

	注意：创建好虚拟环境后，以后运行代码前，需要进入虚拟环境，即执行上面的步骤：2） & 3）

2. 获取代码
	git clone https://github.com/chenchampion/djangosample.git

3. 安装django需要的组件
	1). cd djangosample
	2). pip install -r requirements.txt

4. 初始化项目
	1). python manage.py makemigrations
	2). python manage.py migrate
	3). python manage.py createsuperuser (按照提示，创建项目的超级用户，即网站管理员)

5. 运行项目
	python manage.py runserver 0.0.0.0:8000
