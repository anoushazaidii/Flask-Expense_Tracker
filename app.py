from flask import Flask, render_template, url_for, flash, redirect, request
from flask_login import LoginManager, login_user, current_user, logout_user, login_required, UserMixin
from Expense_form import ExpenseForm, RegistrationForm, LoginForm, IncomeForm, BudgetForm
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///finance.db"
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)
migrate = Migrate(app, db)  # Initialize Flask-Migrate

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

class newuser(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    expenses = db.relationship('Expense', backref='owner', lazy=True)
    incomes = db.relationship('Income', backref='owner', lazy=True)
    budget = db.Column(db.Float, nullable=True, default=0.0)
    monthly_income = db.Column(db.Float, nullable=True)  


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('newuser.id'), nullable=False)

class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('newuser.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return newuser.query.get(int(user_id))

@app.route("/")
@app.route("/home")
def home():
    if current_user.is_authenticated:
        user_expenses = Expense.query.filter_by(user_id=current_user.id).all()
        if user_expenses:
            monthly_income = current_user.monthly_income
            current_month = datetime.now().strftime('%B %Y')
            monthly_expenses = sum(expense.amount for expense in user_expenses)
            monthly_categories = {}
            for expense in user_expenses:
                if expense.category in monthly_categories:
                    monthly_categories[expense.category] += expense.amount
                else:
                    monthly_categories[expense.category] = expense.amount
            
            top_categories = sorted(monthly_categories.items(), key=lambda item: item[1], reverse=True)[:3]
            top_categories = dict(top_categories)
            recent_expenses = sorted(user_expenses, key=lambda x: x.date, reverse=True)[:5]
    
            return render_template('home.html', 
                                   monthly_income=monthly_income,
                                   current_month=current_month, 
                                   monthly_expenses=monthly_expenses, 
                                   monthly_categories=monthly_categories, 
                                   top_categories=top_categories, 
                                   recent_expenses=recent_expenses)
        else:
            return render_template('home.html', no_expenses=True)
    else:
        return render_template('home.html', no_expenses=False)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = newuser(username=form.username.data, email=form.email.data, password=form.password.data,monthly_income=form.monthly_income.data)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = newuser.query.filter_by(email=form.email.data).first()
        if user and user.password == form.password.data:
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/add_expense", methods=['GET', 'POST'])
@login_required
def add_expense():
    form = ExpenseForm()
    if form.validate_on_submit():
        expense = Expense(date=form.date.data, amount=form.amount.data, category=form.category.data, user_id=current_user.id)
        db.session.add(expense)
        db.session.commit()
        flash('Your expense has been added!', 'success')
        return redirect(url_for('home'))
    return render_template('add_expense.html', title='Add Expense', form=form)

@app.route("/add_income", methods=['GET', 'POST'])
@login_required
def add_income():
    form = IncomeForm()
    if form.validate_on_submit():
        income = Income(date=form.date.data, amount=form.amount.data, source=form.source.data, user_id=current_user.id)
        db.session.add(income)
        db.session.commit()
        flash('Your income has been added!', 'success')
        return redirect(url_for('home'))
    return render_template('add_income.html', title='Add Income', form=form)

@app.route("/set_budget", methods=['GET', 'POST'])
@login_required
def set_budget():
    form = BudgetForm()
    if form.validate_on_submit():
        current_user.budget = form.budget.data
        db.session.commit()
        flash('Your budget has been set!', 'success')
        return redirect(url_for('home'))
    return render_template('set_budget.html', title='Set Budget', form=form)

@app.route("/reports")
@login_required
def reports():
    user_expenses = Expense.query.filter_by(user_id=current_user.id).all()
    user_incomes = Income.query.filter_by(user_id=current_user.id).all()
    monthly_income = current_user.monthly_income
    total_expenses = sum(expense.amount for expense in user_expenses)
    total_incomes = sum(income.amount for income in user_incomes) + monthly_income
    budget = current_user.budget

    return render_template('reports.html', 
                           title='Reports', 
                           total_expenses=total_expenses, 
                           total_incomes=total_incomes, 
                           budget=budget,
                           monthly_income=monthly_income
                           )

if __name__ == "__main__":
    app.run(debug=True, port=8000)
