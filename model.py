from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import calculator
from datetime import timedelta, date


app = Flask(__name__)

DB_URI = "sqlite:///model.db"

db = SQLAlchemy()

################################################################################
# Model Definitions


class User(db.Model):
    """Run calculator user"""

    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(50), unique=True)
    weekly_mileage = db.Column(db.Integer, nullable=True)
    # TODO(kara): if time change units on weekly_mileage

    def greet(self):
        """Greet using email"""
        return "Hello, {}".format(self.email)

    def paces(self, intensity):
        """Return object of Pace class"""

        # finds users most recent race
        most_recent_race = Race.query.filter(Race.user_id == self.user_id).order_by(Race.race_id.desc()).first()
        # __init__ on Pace looks like: Pace(self, VDOT, intensity(as string))
        VDOT = most_recent_race.VDOT()
        pace_obj = Pace(VDOT, intensity)
        return pace_obj

    def most_recent_race(self):
        """Return most recent Race object for a user"""
        race = Race.query.filter(Race.user_id == self.user_id).order_by(Race.race_id.desc()).first()
        return race

    def training_plan(self):
        """Return TrainingPlan based on user's most recent race"""
        return TrainingPlan(self)

    def __repr__(self):
        """Provide helpful representation when printed"""

        string = "<User id = {} Max Weekly Mileage = {}>"
        return string.format(self.user_id, self.weekly_mileage)


class Race(db.Model):
    """Store user's races"""

    __tablename__ = "races"

    race_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    # distance in meters
    distance = db.Column(db.Integer, nullable=False)
    # time in minutes
    time = db.Column(db.Integer, nullable=False)

    user = db.relationship("User", backref=db.backref("races", order_by=race_id))

    def VDOT(self):
        """Return user VDOT"""

        percent_VO2 = calculator.get_percent_VO2max(self.time)
        vel = calculator.velocity(self.distance, self.time)
        race_VO2 = calculator.get_VO2_from_velocity(vel)
        VDOT = race_VO2 / percent_VO2

        return VDOT

    def __repr__(self):
        """Provide helpful representation when printed"""

        string = "<Race id: {}, User id: {}, distance: {}, time: {}>"

        return string.format(self.race_id, self.user_id, self.distance, self.time)


class Pace(object):
    """Store paces Easy, Marathon, and Temo as range of percentages

    methods allow the range for each intensity to be returned as objects of
    pace class in velocity or minutes/mile
    """

    PACE_DICT = {
        "easy": (0.55, 0.65, 0.74),
        "marathon": (0.75, 0.79, 0.84),
        "tempo": (0.83, 0.86, 0.89)
    }

    def __init__(self, VDOT, intensity):
        self.VDOT = VDOT
        self.intensity = intensity

    def pace_range(self):
        """Return the range of times in minutes/mile for a given intensity"""

        intensity_tuple = self.PACE_DICT[self.intensity]
        p_range = []
        for t in intensity_tuple:
            percent_VDOT = self.VDOT * t
            velocity = calculator.get_velocity_from_VO2(percent_VDOT)
            miles_per_min = velocity / 1609.34
            minutes_per_mile = 1 / miles_per_min
            # minutes_per_mile = timedelta(minutes=(1/miles_per_min))
            p_range.append(timedelta(minutes=minutes_per_mile))
        return p_range

    def velocity(self):
        """Return list of velocity (low, avg, high) in meters/minute for a given intensity"""

        intensity_tuple = self.PACE_DICT[self.intensity]
        velocity_range = []
        for t in intensity_tuple:
            percent_VDOT = self.VDOT * t
            velocity = calculator.get_velocity_from_VO2(percent_VDOT)
            velocity_range.append(velocity)
        return velocity_range

    def convert_timedelta(self):
        """Return list of pace times (low, avg, high) converted from timedelta object"""

         #        >>> test = [1, 2, 3, 4, 5, 6, 7]
         #        >>> test1 = test[-5:]
         #        >>> print test1
         #        >>> [3, 4, 5, 6, 7]
         # TODO(kara): rewrite using list comp, and time date method .total_seconds

        p_range = self.pace_range()
        time_range = []
        for i in p_range:
            time_str = str(i)
            token_time = time_str.split(".")
            time = token_time[0]
            time = time[-5:]
            time_range.append(time)
        return time_range

    def __repr__(self):
            """Provide a useful representation when printed"""

            string = "<Paces as tuple of VDOT percentage for {} intensity>"
            return string.format(self.intensity)


class TrainingPlan(object):
    """Return list of 18 Week objects for a user

    each Week object contains a tuple of Workout objects
    each Workout object contains a tuple of Segment objects
    """

    def __init__(self, user):
        self.weeks = []
        self.days = self.make_list_of_days()

        # week 1 - 3
        self.weeks.append(Week(user, 0.60, plan=self, workouts=()))
        self.weeks.append(Week(user, 0.60, plan=self, workouts=()))
        self.weeks.append(Week(user, 0.60, plan=self, workouts=()))
        # week 4 - 6
        self.weeks.append(Week(user, 0.60, plan=self, workouts=(
            Workout(
                Segment(intensity='easy', user=user, distance_as_percent=0.162),
            ),
        )))
        self.weeks.append(Week(user, 0.60, plan=self, workouts=(
            Workout(
                Segment(intensity='easy', user=user, distance_as_percent=0.162),
            ),
        )))
        self.weeks.append(Week(user, 0.60, plan=self, workouts=(
            Workout(
                Segment(intensity='easy', user=user, distance_as_percent=0.162),
            ),
        )))
        # weeks 7 & 8
        self.weeks.append(Week(user, 0.80, plan=self, workouts=(
            Workout(
                # this workout calls for the shorter of these two segments
                (Segment(intensity='easy', user=user, distance_as_percent=0.216),
                 Segment(intensity='easy', user=user, time=150)),
                ),
            Workout(
                Segment(intensity='tempo', user=user, rep=2, time=10, rest=1),
            ),
        )))
        self.weeks.append(Week(user, 0.80, plan=self, workouts=(
            Workout(
                # this workout calls for the shorter of these two segments
                (Segment(intensity='easy', user=user, distance_as_percent=0.216),
                 Segment(intensity='easy', user=user, time=150)),
            ),
            Workout(
                Segment(intensity='tempo', user=user, rep=2, time=10, rest=1),
            ),
        )))
        # week 9
        self.weeks.append(Week(user, 0.70, plan=self, workouts=(
            Workout(
                Segment(intensity='easy', user=user, distance_as_percent=0.0945),
                Segment(intensity='easy', user=user, distance_as_percent=0.0945),
            ),
            Workout(
                Segment(intensity='tempo', user=user, rep=2, time=15, rest=1),
            ),
        )))
        # week 10 and 11
        self.weeks.append(Week(user, 0.90, plan=self, workouts=(
            Workout(
                # this workout calls for the shorter of these two segments
                (Segment(intensity='easy', user=user, distance_as_percent=0.243),
                 Segment(intensity='easy', user=user, time=150)),
            ),
            Workout(
                Segment(intensity='tempo', user=user, rep=3, time=10, rest=1),
            ),
        )))
        self.weeks.append(Week(user, 0.90, plan=self, workouts=(
            Workout(
                # this workout calls for the shorter of these two segments
                (Segment(intensity='easy', user=user, distance_as_percent=0.243),
                 Segment(intensity='easy', user=user, time=150)),
            ),
            Workout(
                Segment(intensity='tempo', user=user, rep=3, time=10, rest=1),
            ),
        )))
        # week 12
        self.weeks.append(Week(user, 0.70, plan=self, workouts=(
            Workout(
                # this workout calls for the shorter of these two segments
                (Segment(intensity='marathon', user=user, distance_in_miles=12),
                 Segment(intensity='marathon', user=user, time=120)),
            ),
            Workout(
                Segment(intensity='tempo', user=user, rep=2, time=15, rest=1),
            ),
        )))
        # week 13
        self.weeks.append(Week(user, 1.0, plan=self, workouts=(
            Workout(
                Segment(intensity='tempo', user=user, rep=3, time=5, rest=1),
                Segment(intensity='easy', user=user, time=60),
                Segment(intensity='tempo', user=user, rep=3, time=5, rest=1),
            ),
            Workout(
                Segment(intensity='tempo', user=user, rep=2, time=10, rest=2),
                Segment(intensity='easy', user=user, time=75)
                ),
        )))
        # week 14
        self.weeks.append(Week(user, 0.90, plan=self, workouts=(
            Workout(
                # this workout calls for the shorter of these two segments
                (Segment(intensity='marathon', user=user, distance_in_miles=15),
                 Segment(intensity='marathon', user=user, time=150)),
            ),
            Workout(
                Segment(intensity='tempo', user=user, rep=2, time=10, rest=2),
                Segment(intensity='easy', user=user, time=75),
            ),
        )))
        # week 15
        self.weeks.append(Week(user, 1.0, plan=self, workouts=(
            Workout(
                Segment(intensity='easy', user=user, distance_as_percent=0.25),
            ),
            Workout(
                Segment(intensity='tempo', user=user, rep=2, time=10, rest=2),
                Segment(intensity='easy', user=user, time=75),
            ),
        )))
        # week 16
        self.weeks.append(Week(user, 0.80, plan=self, workouts=(
            Workout(
                Segment(intensity='tempo', user=user, rep=3, time=5, rest=1),
                Segment(intensity='easy', user=user, time=60),
                Segment(intensity='tempo', user=user, rep=3, time=5, rest=1),
            ),
            Workout(
                Segment(intensity='tempo', user=user, rep=2, time=10, rest=2),
                Segment(intensity='easy', user=user, time=75),
            ),
        )))
        # week 17
        self.weeks.append(Week(user, 0.80, plan=self, workouts=(
            Workout(
                # this workout calls for the shorter of these two segments
                (Segment(intensity='marathon', user=user, distance_in_miles=12),
                 Segment(intensity='marathon', user=user, time=120)),
            ),
            Workout(
                Segment(intensity='easy', user=user, distance_in_miles=2),
                Segment(intensity='tempo', user=user, rep=5, time=5, rest=1),
            ),
        )))
        # week 18
        self.weeks.append(Week(user, 0.60, plan=self, workouts=(
            Workout(
                Segment(intensity='easy', user=user, distance_as_percent=0.081),
                Segment(intensity='easy', user=user, distance_as_percent=0.081),
            ),
            Workout(
                Segment(intensity='easy', user=user, distance_in_miles=2),
                Segment(intensity='tempo', user=user, rep=5, time=5, rest=1),
            ),
        )))

    def make_list_of_days(self):
        """Makes list of the calendar datetime objects for the training_plan

        to return the day use datetime class attr: .day
        to return the YYYY_MM_DD (ISO 8601) format use instance method: .isoformat()
        see python docs for additional datetime methods
        """

        days = []
        today = date.today()
        # start_date will be the next Monday
        day_of_week = today.weekday()
        offset = -day_of_week % 7
        start_date = today + timedelta(days=offset)
        # 18 weeks * 7 day/week = 126 days,
        for i in range(126):
            current_day = start_date + timedelta(days=i)
            days.append(current_day)
        return days


class Week(object):
    """Returns x days of training as a list

    Uses user race.VDOT to determine distance of workouts, and remainder of
    peak mileage to assign distances to non-quality days.

    The lesser of two workouts my be selected for by passing workouts in as a tuple
    """
# TODO(kara): if time change units on User.weekly_mileage
    def __init__(self, user, percent_peak_mileage, plan, workouts, days=6):
        self.user = user
        #  percent_peak_mileage is specified for each TP, must pass in.
        self.percent_peak_mileage = percent_peak_mileage
        # user_id from User class/instance, as class method
        self.peakmileage = calculator.miles_to_meters(user.weekly_mileage)
        self.week_in_meters = (self.percent_peak_mileage * self.peakmileage)
        # self.week_in_miles = (self.percent_peak_mileage * self.peakmileage)
        self.plan = plan
        self.days = days
        self.quality_distance = sum(workout.distance for workout in workouts)
        self.workouts = self.create_remaining_days(workouts)
        for workout in self.workouts:
            workout.week = self
        self.distance = sum(workout.distance for workout in self.workouts)
        # print "WEEK DIST: ", self.distance

    def create_remaining_days(self, workouts):
        """Return dynamicaly-generated remaining training days"""

        # find remaining number of user specified days
        days = self.days - len(workouts)
        # print "NUM days: ", days
        # print "week_in_meters: ", self.week_in_meters
        # print "quality_distance ", self.quality_distance
        # find remaining distance
        rem_dist = self.week_in_meters - self.quality_distance
        # divide rem_dist between remaining days
        distance = rem_dist/days
        # for each remaining day create an instance of Workout, intensity=easy
        for i in range(days):
            seg = Segment(intensity="easy", user=self.user)
            seg.distance = distance
            workout = Workout(seg)
            workouts = workouts + (workout,)
        # adjust if user specified days is less than 7
        remainder_of_seven = 7 - len(workouts)
        for i in range(remainder_of_seven):
            workouts = workouts + (Workout(),)
        return workouts

    def show_week(self):
        """String representation of week distance. For user display"""

        # convert meters to miles to display, see all show_ functions if changed
        miles = calculator.meters_to_miles(self.distance)
        return "Week Distance: {0:.2f}".format(miles)


class Workout(object):
    """Return tuple of segments

    A single workout is a tuple of segments
    'quality days', specific instructions for workouts with distance, time, pace attributes

    """
    # workout is a list of segments, segments = (segment, segment, segment....)
    # segments should only accept a tuple
    # use segment.distance() to get distance of workout.

    def __init__(self, *segments):
        self.segments = self.final_segments(segments)
        self.distance = sum(seg.calc_distance() for seg in self.segments)
        # print "workout distance: ", self.distance
        self.week = None

    def final_segments(self, segments):
        """Return the less of two segments when tuple passed for segment"""

        # make new tuple to hold individual segment objects
        final_segments = ()
        # loop over segments to:
            # find shortest in a tuple, construct tuple of just segment objects
            # assign the 'parent' workout
        for i in range(len(segments)):
            segment = segments[i]
            if isinstance(segment, tuple):
                tup = segment
                # find smaller segment in the tuple
                seg = min(tup, key=lambda x: x.distance)
                # add smaller segment to tuple
                final_segments = final_segments + (seg,)
                seg.workout = self
            # add all other segment objects to the tuple
            else:
                final_segments = final_segments + (segment,)
            # adds bi-directional accountability, linked to parent instance
                segment.workout = self
        return final_segments

    def show_workout(self):
        """String representation of workout distance. For user display"""

        if self.distance:
            # convert meters to miles to display, see all show_ functions if changed
            miles = calculator.meters_to_miles(self.distance)
            return "Workout Distance: {0:.2f}".format(miles)
        return "Rest day"
        # A Workout() without *segments returns 0 for self.distance.
        # because distance determined by segements.
        # Segments will be generated up to the number of training days specified
        # with in Week. Any of the remaining 7 week days will be generated as
        # blank days and labled "Rest day" for display


class Segment(object):
    """Pace() and distance or time components of a workout"""

# TODO(kara): unit test distance calculations

    def __init__(self, intensity, user, workout=None, rep=1, time=None, distance_in_miles=None,
                 distance_as_percent=None, rest=None):

        # intensity is the STRING: "easy", "marathon", or "tempo"
        self.intensity = intensity
        # when segment is called from the User class user_id will not need to be passed in
        self.user = user
        # uses instance method from User class
        self.pace = user.paces(self.intensity)
        self.rep = rep
        self.time = time
        if time:
            self.total_time = time * rep
        # explanation of self.distance from time: if the segment was asked
        # self.dist when only time is given it should not return a value. you are
        # running for time specifically. A workout can determine an aprox. of
        # distance of any segment using calc_distance()
        self.rest = rest
        # adds bi-directional accountability, linked to parent instance
        self.workout = None
        # peakmileage in meters
        peakmileage = calculator.miles_to_meters(self.user.weekly_mileage)
        self.distance = None
        if distance_as_percent:
            self.distance = (distance_as_percent * peakmileage)
        # in meters
        if distance_in_miles:
            self.distance = calculator.miles_to_meters(distance_in_miles)

    def calc_distance(self):
        """Return distance covered in a segment. """
        # needs to determine distance uses pace.velocity OR self.distance * time
        if self.time:
            velocity_range = self.pace.velocity()
            distance = velocity_range[1] * self.total_time
        else:
            distance = self.distance
        return distance

    def show_segment(self):
        """Return tuple containing string representation of the segment, for user display"""

        seg_tuple = ()
        if self.pace:
            intensity_as_string = self.intensity.capitalize()
            pace_as_time = self.pace.convert_timedelta()
            pace = "{} pace: {} ".format(intensity_as_string, pace_as_time[1])
            seg_tuple += (pace,)
        if self.rep > 1:
            reps = "Reps: {} x {} min. ".format(self.rep, self.time)
            seg_tuple += (reps,)
        if self.rep == 1 and self.time:
            time = "Time: {} ".format(self.total_time)
            seg_tuple += (time,)
        if self.rest:
            rest = "Rest: {} min. ".format(self.rest)
            seg_tuple += (rest,)
        if self.distance:
            # convert meters to miles to display, see all show_ functions if changed
            miles = calculator.meters_to_miles(self.distance)
            distance = "Distance: {0:.2f} miles ".format(miles)
            seg_tuple += (distance,)

        return seg_tuple

    def __repr__(self):
        """Return string representation of segment"""

        string = "<Intensity: {}, reps: {}, time: {}, rest: {}>"
        return string.format(self.intensity, self.rep, self.time, self.rest)

################################################################################
# Helper Functions


def connect_to_db(app):
    """Connect to the database."""
    with app.app_context():
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///model.db'
        app.config['SQLALCHEMY-ECHO'] = True
        db.app = app
        db.init_app(app)
        db.create_all()

connect_to_db(app)

print("Connected to Model.db")
