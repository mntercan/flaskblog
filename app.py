from flask import Flask,render_template,url_for,redirect,request,flash,session,abort
import os
from PIL import Image
import secrets
from flask_wtf import FlaskForm
from wtforms import  StringField,PasswordField,TextField,SubmitField,BooleanField,TextField,TextAreaField,FileField
from wtforms.validators import DataRequired,InputRequired
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.file import FileAllowed
from datetime import datetime
from flask_bcrypt import Bcrypt
from flask_login import LoginManager,login_user,current_user,UserMixin,logout_user,login_required
app = Flask(__name__)
SECRET_KEY = os.urandom(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SECRET_KEY'] = SECRET_KEY
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


def validate_email(args):
    return User.query.filter_by(email=args).first()

def validate_username(args):
    return User.query.filter_by(username=args).first()

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/images', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

class LoginForm(FlaskForm):
    email = StringField('E-Posta Adresi', validators=[DataRequired()])
    password = PasswordField('Şifre',validators=[DataRequired()])
    remember = BooleanField('Beni Hatırla')
    submit = SubmitField('Giriş Yap')

class RegisterForm(FlaskForm):
    name = StringField('Kullanıcı Adı', validators=[DataRequired()])
    email = StringField('E-Posta Adresi',validators=[DataRequired()])
    password = PasswordField('Şifre',validators=[DataRequired()])
    picture  = FileField('Kullanıcı Profil Resmi',validators=[FileAllowed(['jpg','png'])])
    submit = SubmitField('Kayıt Ol')

class PostForm(FlaskForm):
    posttitle = StringField('Post Başlığı',validators=[DataRequired()])
    postcontent= TextAreaField('Post İçeriği',validators=[DataRequired()])
    submit = SubmitField('Postu Ekle')

class UpdateAccount(FlaskForm):
    name = StringField('Kullanıcı Adı', validators=[DataRequired()])
    email = StringField('E-Posta Adresi',validators=[DataRequired()])
    password = PasswordField('Şifre',validators=[DataRequired()])
    picture  = FileField('Kullanıcı Profil Resmi',validators=[FileAllowed(['jpg','png'])])
    submit = SubmitField('Güncelle')

class Edit(FlaskForm):
    title = StringField('Post Başlığı')
    content = TextAreaField('Post İçeriği')
    submit = SubmitField('Kaydet')

class User(db.Model,UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')



class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    yazan = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)




@app.route("/")
def index():
    q = request.args.get('q')
    if q: 
        posts = Post.query.filter(Post.title.contains(q)|Post.content.contains(q))
    else:
        posts = Post.query.order_by(Post.date_posted.desc()).all()
    return render_template('index.html',posts=posts)

@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
        post = Post.query.filter_by(id=post_id).one()
        db.session.delete(post)
        db.session.commit()
        flash(u'Postunuz Silinmiştir','success')
        return redirect(url_for('index'))

@app.route("/account",methods=['POST','GET'])
def account():
    if current_user.is_authenticated:
        form = UpdateAccount()
        if form.validate_on_submit():
            if bcrypt.check_password_hash(current_user.password, form.password.data):
                current_user.username = form.name.data
                current_user.email = form.email.data
                db.session.commit()
                flash('Hesabınız Güncellendi!', 'success')
                return redirect(url_for('account'))
            else:
                flash('Yanlış Şifre','error')
                return redirect(url_for('account'))
        elif request.method == 'GET':
                form.name.data = current_user.username
                form.email.data = current_user.email
                image_dosyası = url_for('static', filename='images/' + current_user.image_file)
                return render_template('account.html',profilimg=image_dosyası, form=form)
    else:
        return redirect(url_for('index'))
@app.route("/login",methods=['POST','GET'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash(u'Başarıyla Giriş Yapıldı','success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash(u'Girilen Bilgilere Ait Kullanıcı Yok','error')
            return redirect(url_for('index'))
    return render_template('login.html',form=form)

@app.route("/register",methods=['POST','GET'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if validate_email(form.email.data):
            flash(u'Bu E-Posta Önceden Alınmış','error')
            return render_template('register.html',form=form)
        if validate_username(form.name.data):
            flash(u'Bu Kullanıcı Adı Önceden Alınmış','error')
            return render_template('register.html',form=form)
        else:
            picture_file = save_picture(form.picture.data)
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = User(username=form.name.data, email=form.email.data, password=hashed_password,image_file=picture_file)
            db.session.add(user)
            db.session.commit()
            flash(u'Hesabınız Oluşturuldu!','success')
        return redirect(url_for('login'))
    return render_template('register.html',form=form)

@app.route("/newpost",methods=['POST','GET'])
@login_required
def newpost():
    if current_user.is_authenticated:
        form = PostForm()
        if form.validate_on_submit():
                post = Post(user_id=current_user.id,title=form.posttitle.data,date_posted=datetime.utcnow(),content=form.postcontent.data,yazan=current_user.username)
                db.session.add(post)
                db.session.commit()
                return redirect(url_for('index'))
        return render_template('newpost.html',form=form)
    else:
        return redirect(url_for('index'))

@app.route("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))



@app.route("/post/<int:post_id>",methods=['POST','GET'])
def post(post_id):
    form = Edit()
    post = Post.query.filter_by(id=post_id).one()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        return redirect(url_for('post',post_id=post.id))
    elif request.method == 'GET':
            form.title.data = post.title
            form.content.data = post.content
    return render_template('post.html',post=post,form=form)

if __name__ == "__main__":
    app.run(debug=True)