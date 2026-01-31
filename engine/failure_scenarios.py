"""
Failure Scenario Definitions for Synthetic Data Generation

Each scenario defines how sensor values change over time to simulate
realistic failure modes in chiller systems. These are based on:
- ASHRAE maintenance guidelines
- Equipment manufacturer documentation  
- Real-world failure mode observations
- Industry case studies

Scenarios are the "failure stories" that demonstrate the value
of predictive maintenance - catching problems before they become
expensive failures.
"""

from dataclasses import dataclass, field
from typing import Dict, Callable, Optional, List
from enum import Enum
import math


class FailureType(Enum):
    """Types of failure modes that can be simulated."""
    HEALTHY = "healthy"
    TUBE_FOULING = "tube_fouling"
    BEARING_WEAR = "bearing_wear"
    REFRIGERANT_LEAK = "refrigerant_leak"
    ELECTRICAL_ISSUE = "electrical_issue"
    LOW_LOAD_INEFFICIENCY = "low_load_inefficiency"
    POST_MAINTENANCE_MISALIGNMENT = "post_maintenance_misalignment"


@dataclass
class FailureScenario:
    """
    Definition of a failure scenario for simulation.
    
    A scenario describes how sensor values should evolve over time
    to realistically simulate a specific failure mode. Each scenario
    includes the physics-based "story" of why values change.
    
    Attributes:
        name: Human-readable scenario name
        failure_type: Type of failure being simulated
        description: Technical description of the failure mode
        duration_days: Typical duration of the failure progression
        story: Narrative explanation for demos/documentation
        modifiers: Functions that modify sensor values over time
        
    Modifiers:
        Each modifier is a function with signature:
        (base_value, progress, day) -> modified_value
        
        Where:
        - base_value: The healthy/normal value
        - progress: 0.0 to 1.0 over scenario duration
        - day: Current day number in scenario
    """
    name: str
    failure_type: FailureType
    description: str
    duration_days: int
    story: str
    modifiers: Dict[str, Callable[[float, float, int], float]] = field(default_factory=dict)
    
    def apply_modifier(
        self,
        metric_name: str,
        base_value: float,
        progress: float,
        day: int
    ) -> float:
        """
        Apply the scenario's modifier to a base value.
        
        Args:
            metric_name: Name of the metric to modify
            base_value: Normal/healthy value
            progress: Scenario progress (0.0 to 1.0)
            day: Current day in scenario
            
        Returns:
            Modified value reflecting the failure progression
        """
        if metric_name in self.modifiers:
            return self.modifiers[metric_name](base_value, progress, day)
        return base_value
    
    def get_affected_metrics(self) -> List[str]:
        """Return list of metrics affected by this scenario."""
        return list(self.modifiers.keys())


class ScenarioLibrary:
    """
    Library of pre-defined failure scenarios.
    
    Each scenario is carefully designed to tell a realistic
    "failure story" that demonstrates the value of early detection.
    
    Usage:
        # Get a specific scenario
        scenario = ScenarioLibrary.tube_fouling(duration_days=60)
        
        # Get all available scenarios
        all_scenarios = ScenarioLibrary.get_all_scenarios()
        
        # Get scenario by type
        scenario = ScenarioLibrary.get_scenario_by_type(FailureType.BEARING_WEAR)
    """
    
    @staticmethod
    def healthy_operation(duration_days: int = 30) -> FailureScenario:
        """
        Normal healthy chiller operation.
        
        All parameters stay within normal ranges with only
        minor random variations from load and ambient changes.
        """
        return FailureScenario(
            name="Healthy Operation",
            failure_type=FailureType.HEALTHY,
            description="Normal chiller operation with stable performance metrics",
            duration_days=duration_days,
            story="""
            📊 HEALTHY OPERATION SCENARIO
            ════════════════════════════════════════════
            
            The chiller is operating normally with all parameters
            within expected ranges.
            
            Observations:
            • Approach temperature: 2-3°C (stable)
            • kW/Ton: 0.55-0.70 (good efficiency)
            • Vibration: 1.5-2.5 mm/s (smooth operation)
            • Phase imbalance: <2% (balanced)
            
            Health Score: 85-95
            
            Action Required: None - continue normal monitoring
            ════════════════════════════════════════════
            """,
            modifiers={
                # No modifiers - healthy operation uses base values
            }
        )
    
    @staticmethod
    def tube_fouling(duration_days: int = 60) -> FailureScenario:
        """
        Gradual condenser tube fouling scenario.
        
        This is the "million-dollar insight" scenario. Condenser
        tube fouling is one of the most expensive problems in
        chiller operation because it:
        - Increases energy consumption 2-3% per °C of approach rise
        - Often goes undetected until severe
        - Can lead to high head pressure trips
        - Costs $50,000-$150,000+ annually if undetected
        
        Physics:
        - Fouling reduces heat transfer coefficient
        - Same heat rejection requires higher temperature difference
        - Approach temperature increases
        - Condensing pressure rises
        - Compressor works harder (higher kW/ton)
        """
        def approach_modifier(base: float, progress: float, day: int) -> float:
            """Approach increases from ~2.5°C to ~6.5°C over duration."""
            # Fouling growth is slightly exponential (accelerates)
            increase = 4.0 * (progress ** 1.3)
            # Add some daily variation
            daily_noise = 0.2 * math.sin(day * 0.5)
            return base + increase + daily_noise
        
        def kw_per_ton_modifier(base: float, progress: float, day: int) -> float:
            """Efficiency degrades as fouling worsens."""
            # Each degree of approach costs ~2-3% efficiency
            # 4°C rise ≈ 8-12% efficiency loss ≈ 0.08-0.12 kW/ton increase
            increase = 0.15 * progress
            return base + increase
        
        def cdw_outlet_modifier(base: float, progress: float, day: int) -> float:
            """CDW outlet rises as heat transfer degrades."""
            increase = 2.5 * progress
            return base + increase
        
        def power_modifier(base: float, progress: float, day: int) -> float:
            """Power consumption increases with degraded efficiency."""
            increase_factor = 1.0 + (0.12 * progress)  # Up to 12% increase
            return base * increase_factor
        
        return FailureScenario(
            name="Condenser Tube Fouling",
            failure_type=FailureType.TUBE_FOULING,
            description="Gradual buildup of scale, biofilm, and debris in condenser tubes reducing heat transfer",
            duration_days=duration_days,
            story="""
            💰 TUBE FOULING SCENARIO - "The Million-Dollar Insight"
            ════════════════════════════════════════════════════════
            
            Week 1-2: Normal operation
            • Approach temp: ~2.5°C ✅
            • kW/Ton: ~0.62 ✅
            • Health Score: 90+
            
            Week 3-4: Early warning signs
            • Approach temp: ~3.2°C ⚠️ (Early detection opportunity!)
            • kW/Ton: ~0.65
            • Health Score: 82
            
            Week 5-6: Degradation confirmed  
            • Approach temp: ~4.0°C 🔶
            • kW/Ton: ~0.70
            • Health Score: 72
            
            Week 7-8: Efficiency loss measurable
            • Approach temp: ~5.2°C 🔴
            • kW/Ton: ~0.75
            • Health Score: 58
            
            Week 9+: Critical fouling
            • Approach temp: >6°C 🔴🔴
            • kW/Ton: >0.80
            • Health Score: <50
            
            ════════════════════════════════════════════════════════
            💵 COST IMPACT IF UNDETECTED:
            • Energy waste: 15-25%
            • Annual cost: $50,000 - $150,000+
            • Risk: High head pressure trips, capacity loss
            
            ✅ VALUE OF EARLY DETECTION (Week 3-4):
            • Simple tube cleaning: $5,000 - $15,000
            • Prevented energy waste: $40,000+
            • Avoided emergency repairs and downtime
            ════════════════════════════════════════════════════════
            """,
            modifiers={
                "approach_temp": approach_modifier,
                "kw_per_ton": kw_per_ton_modifier,
                "cdw_outlet_temp": cdw_outlet_modifier,
                "power_kw": power_modifier,
            }
        )
    
    @staticmethod
    def bearing_wear(duration_days: int = 45) -> FailureScenario:
        """
        Progressive compressor bearing wear scenario.
        
        Bearing wear is a leading cause of compressor failure.
        Early detection via vibration monitoring can prevent
        catastrophic failure and allow planned replacement.
        
        Physics:
        - Bearing surface degradation increases friction
        - Metal-to-metal contact creates vibration
        - Specific bearing defect frequencies appear
        - Heat generation increases (if severe)
        - Eventually leads to seizure if unaddressed
        """
        def vibration_modifier(base: float, progress: float, day: int) -> float:
            """Vibration increases non-linearly (accelerates near failure)."""
            # Exponential growth pattern
            increase = 8.0 * (progress ** 2.0)
            # Add bearing rotation effects
            periodic = 0.5 * math.sin(day * 0.3) * progress
            return base + increase + periodic
        
        def vibration_freq_modifier(base: float, progress: float, day: int) -> float:
            """Bearing defect frequencies may appear as wear progresses."""
            if progress > 0.5:
                # Bearing defect frequency appears
                return base * (1.0 + 0.3 * (progress - 0.5))
            return base
        
        def power_modifier(base: float, progress: float, day: int) -> float:
            """Power increases slightly due to friction in late stages."""
            if progress > 0.7:
                friction_factor = 1.0 + 0.05 * (progress - 0.7) / 0.3
                return base * friction_factor
            return base
        
        def current_modifier(base: float, progress: float, day: int) -> float:
            """Current may increase with mechanical load."""
            if progress > 0.6:
                return base * (1.0 + 0.03 * (progress - 0.6) / 0.4)
            return base
        
        return FailureScenario(
            name="Compressor Bearing Wear",
            failure_type=FailureType.BEARING_WEAR,
            description="Progressive wear of compressor shaft bearings leading to increased vibration",
            duration_days=duration_days,
            story="""
            ⚙️ BEARING WEAR SCENARIO
            ════════════════════════════════════════════════════════
            
            Week 1-2: Baseline
            • Vibration: ~2.0 mm/s ✅
            • Smooth, quiet operation
            • Health Score: 92
            
            Week 3: Slight increase
            • Vibration: ~3.0 mm/s ✅ (still within limits)
            • Health Score: 85
            • Detection: Trending shows upward pattern
            
            Week 4: Attention level
            • Vibration: ~4.5 mm/s ⚠️
            • Health Score: 72
            • Action: Schedule vibration analysis
            
            Week 5: Action required
            • Vibration: ~6.0 mm/s 🔶
            • Health Score: 58
            • Action: Plan bearing inspection/replacement
            
            Week 6+: Critical
            • Vibration: >8.0 mm/s 🔴
            • Possible harmonic frequencies appearing
            • Health Score: <45
            • Risk: Imminent bearing failure
            
            ════════════════════════════════════════════════════════
            💵 COST COMPARISON:
            
            ❌ Undetected Failure:
            • Catastrophic compressor damage
            • Repair cost: $50,000 - $200,000
            • Downtime: 2-6 weeks
            • Emergency repair premium: 50-100%
            
            ✅ Early Detection (Week 4):
            • Planned bearing replacement: $5,000 - $15,000
            • Scheduled during low-demand period
            • Downtime: 2-3 days
            • No secondary damage
            ════════════════════════════════════════════════════════
            """,
            modifiers={
                "vibration_rms": vibration_modifier,
                "vibration_freq": vibration_freq_modifier,
                "power_kw": power_modifier,
                "current_r": current_modifier,
                "current_y": current_modifier,
                "current_b": current_modifier,
            }
        )
    
    @staticmethod
    def refrigerant_leak(duration_days: int = 30) -> FailureScenario:
        """
        Gradual refrigerant loss scenario.
        
        Refrigerant leaks cause:
        - Reduced cooling capacity
        - Poor efficiency
        - Potential compressor damage (oil circulation issues)
        - Environmental compliance issues
        """
        def kw_per_ton_modifier(base: float, progress: float, day: int) -> float:
            """Efficiency degrades significantly with low charge."""
            increase = 0.35 * progress  # Up to 35% efficiency loss
            return base + increase
        
        def delta_t_modifier(base: float, progress: float, day: int) -> float:
            """Delta-T decreases as capacity falls."""
            reduction = 2.5 * progress
            return max(base - reduction, 1.5)  # Min delta-T
        
        def approach_modifier(base: float, progress: float, day: int) -> float:
            """Approach behavior with low charge."""
            # Initially may decrease (less heat to reject)
            # Then increases as system struggles
            if progress < 0.3:
                return base - 0.5 * progress
            else:
                return base + 0.8 * (progress - 0.3)
        
        def load_modifier(base: float, progress: float, day: int) -> float:
            """Apparent load may decrease as capacity falls."""
            if progress > 0.4:
                reduction = 15.0 * (progress - 0.4) / 0.6
                return max(base - reduction, 20.0)
            return base
        
        return FailureScenario(
            name="Refrigerant Leak",
            failure_type=FailureType.REFRIGERANT_LEAK,
            description="Slow loss of refrigerant charge through small leak",
            duration_days=duration_days,
            story="""
            ❄️ REFRIGERANT LEAK SCENARIO
            ════════════════════════════════════════════════════════
            
            Week 1: Initial leak begins
            • Performance still normal
            • No obvious symptoms
            • Health Score: 88
            
            Week 2: Early efficiency drop
            • kW/Ton increasing: 0.65 → 0.72 ⚠️
            • Capacity still adequate
            • Health Score: 78
            • Detection opportunity!
            
            Week 3: Clear performance impact
            • kW/Ton: ~0.80 🔶
            • Delta-T dropping (capacity loss)
            • May not hold setpoint on hot days
            • Health Score: 62
            
            Week 4: Significant degradation
            • kW/Ton: >0.90 🔴
            • Capacity noticeably reduced
            • Compressor running longer
            • Health Score: 48
            
            ════════════════════════════════════════════════════════
            ⚠️ RISKS OF CONTINUED OPERATION:
            • Compressor damage (poor oil return)
            • Complete capacity loss
            • Environmental compliance violation
            • Refrigerant is expensive!
            
            💵 COST IMPACT:
            • Leak repair: $500 - $3,000
            • Refrigerant recharge: $2,000 - $10,000+
            • Compressor damage (if ignored): $20,000 - $50,000
            ════════════════════════════════════════════════════════
            """,
            modifiers={
                "kw_per_ton": kw_per_ton_modifier,
                "delta_t": delta_t_modifier,
                "approach_temp": approach_modifier,
                "load_percent": load_modifier,
            }
        )
    
    @staticmethod
    def electrical_issue(duration_days: int = 14) -> FailureScenario:
        """
        Electrical supply or connection issue scenario.
        
        Phase imbalance is a serious electrical issue that can
        rapidly damage motors through overheating.
        """
        def phase_imbalance_modifier(base: float, progress: float, day: int) -> float:
            """Phase imbalance increases over time."""
            increase = 7.0 * progress
            # Add intermittent spikes (loose connection behavior)
            if day % 3 == 0 and progress > 0.3:
                increase += 2.5
            return base + increase
        
        def current_r_modifier(base: float, progress: float, day: int) -> float:
            """One phase draws progressively more current."""
            return base * (1.0 + 0.15 * progress)
        
        def current_y_modifier(base: float, progress: float, day: int) -> float:
            """Another phase may draw less."""
            return base * (1.0 - 0.08 * progress)
        
        def current_b_modifier(base: float, progress: float, day: int) -> float:
            """Third phase relatively stable."""
            return base * (1.0 + 0.02 * progress)
        
        return FailureScenario(
            name="Electrical Supply Issue",
            failure_type=FailureType.ELECTRICAL_ISSUE,
            description="Voltage imbalance or deteriorating electrical connection causing phase imbalance",
            duration_days=duration_days,
            story="""
            ⚡ ELECTRICAL ISSUE SCENARIO
            ════════════════════════════════════════════════════════
            
            Day 1-3: Minor imbalance appears
            • Phase imbalance: ~2.0% ✅
            • Currents slightly uneven
            • Health Score: 85
            
            Day 4-7: Imbalance increasing
            • Phase imbalance: ~4.0% ⚠️
            • Motor running warmer
            • Health Score: 70
            • Intermittent current spikes observed
            
            Day 8-10: Warning level
            • Phase imbalance: ~5.5% 🔶
            • Motor insulation stress
            • Health Score: 55
            • Investigate electrical supply
            
            Day 11+: Critical
            • Phase imbalance: >7% 🔴
            • Motor life significantly reduced
            • Health Score: <45
            • Risk of motor failure
            
            ════════════════════════════════════════════════════════
            ⚡ ELECTRICAL PHYSICS:
            
            Per NEMA MG-1:
            • 1% voltage imbalance → 6-10% current imbalance
            • Motor heating increases with square of imbalance
            • 5% imbalance → ~25% additional heating
            • Motor life reduced up to 50% with sustained imbalance
            
            🔧 COMMON CAUSES:
            • Loose terminal connections
            • Utility supply problems
            • Failed capacitors
            • Unequal cable impedances
            • Corroded connections
            
            💵 COST IMPACT:
            • Electrical inspection: $500 - $1,500
            • Connection repair: $200 - $1,000
            • Motor rewind (if damaged): $15,000 - $40,000
            • Motor replacement: $25,000 - $75,000
            ════════════════════════════════════════════════════════
            """,
            modifiers={
                "phase_imbalance": phase_imbalance_modifier,
                "current_r": current_r_modifier,
                "current_y": current_y_modifier,
                "current_b": current_b_modifier,
            }
        )
    
    @staticmethod
    def post_maintenance_misalignment(duration_days: int = 7) -> FailureScenario:
        """
        Misalignment after maintenance work scenario.
        
        This demonstrates detection of maintenance-induced issues,
        which are common but often overlooked.
        """
        def vibration_modifier(base: float, progress: float, day: int) -> float:
            """Sudden vibration increase after maintenance."""
            if day == 0:
                # Immediate jump after "maintenance"
                return base + 5.0
            # Slight worsening as misalignment causes wear
            return base + 5.0 + 0.4 * day
        
        def vibration_freq_modifier(base: float, progress: float, day: int) -> float:
            """2x running speed often indicates misalignment."""
            if day > 0:
                return base * 2.0  # 2x fundamental
            return base
        
        return FailureScenario(
            name="Post-Maintenance Misalignment",
            failure_type=FailureType.POST_MAINTENANCE_MISALIGNMENT,
            description="Coupling or shaft misalignment introduced during maintenance work",
            duration_days=duration_days,
            story="""
            🔧 POST-MAINTENANCE MISALIGNMENT SCENARIO
            ════════════════════════════════════════════════════════
            
            Before Maintenance:
            • Vibration: ~2.0 mm/s ✅
            • Smooth operation
            • Health Score: 90
            
            Immediately After Maintenance:
            • Vibration: ~7.0 mm/s 🔴 (sudden jump!)
            • New vibration pattern at 2x frequency
            • Health Score: 52
            
            Day 2-3:
            • Vibration: 7.5+ mm/s 🔴
            • Slight worsening trend
            • Health Score: 48
            • Misalignment causing accelerated wear
            
            Day 4-7:
            • Vibration continues to rise
            • Bearing/seal wear accelerating
            • Coupling wear visible
            • Immediate correction needed
            
            ════════════════════════════════════════════════════════
            🔍 DIAGNOSTIC INDICATORS:
            
            • Sudden vibration increase after maintenance
            • 2x running frequency dominant (classic misalignment)
            • Axial vibration often elevated
            • Coupling temperature may increase
            
            🔧 COMMON CAUSES:
            • Improper shaft alignment procedure
            • Moved equipment not realigned
            • Soft foot condition
            • Piping strain
            • Foundation issues
            
            💵 COST TO CORRECT:
            • Laser alignment: $500 - $2,000
            • Time: 2-4 hours
            
            💵 COST IF IGNORED:
            • Accelerated bearing wear
            • Seal failures
            • Coupling damage
            • Potential shaft damage: $10,000+
            ════════════════════════════════════════════════════════
            """,
            modifiers={
                "vibration_rms": vibration_modifier,
                "vibration_freq": vibration_freq_modifier,
            }
        )
    
    @staticmethod
    def low_load_inefficiency(duration_days: int = 14) -> FailureScenario:
        """
        Extended low-load operation scenario.
        
        Demonstrates that efficiency monitoring must account
        for part-load conditions.
        """
        def load_modifier(base: float, progress: float, day: int) -> float:
            """Load drops and stays low."""
            return 25.0 + 10.0 * math.sin(day * 0.5)  # 15-35% load
        
        def kw_per_ton_modifier(base: float, progress: float, day: int) -> float:
            """kW/ton increases at low load (normal behavior)."""
            # At 25% load, kW/ton is typically 30-50% higher
            return base * 1.40
        
        return FailureScenario(
            name="Low Load Inefficiency",
            failure_type=FailureType.LOW_LOAD_INEFFICIENCY,
            description="Extended operation at low load causing poor efficiency (not a fault)",
            duration_days=duration_days,
            story="""
            📉 LOW LOAD OPERATION SCENARIO
            ════════════════════════════════════════════════════════
            
            This scenario demonstrates normal physics, not a fault.
            
            Chillers are designed for peak load efficiency.
            At low loads (below 30%), efficiency naturally decreases.
            
            Observations:
            • Load: 20-35%
            • kW/Ton: 0.85-1.0 (appears poor but expected)
            • All other parameters normal
            • Health Score: 75-80 (penalized for efficiency)
            
            ════════════════════════════════════════════════════════
            📊 PART-LOAD PHYSICS:
            
            • Fixed losses (fans, pumps, controls) become larger
              percentage of total power at low loads
            • Compressor operates in less efficient range
            • VFD-driven machines perform better at part load
            
            💡 RECOMMENDATIONS:
            • Consider staging (run fewer machines at higher load)
            • Evaluate VFD retrofit for older machines
            • Accept lower efficiency during swing seasons
            • Don't chase efficiency alarms at low load!
            
            This is why context matters in predictive maintenance.
            ════════════════════════════════════════════════════════
            """,
            modifiers={
                "load_percent": load_modifier,
                "kw_per_ton": kw_per_ton_modifier,
            }
        )
    
    @classmethod
    def get_all_scenarios(cls) -> List[FailureScenario]:
        """Return all available pre-built scenarios."""
        return [
            cls.healthy_operation(),
            cls.tube_fouling(),
            cls.bearing_wear(),
            cls.refrigerant_leak(),
            cls.electrical_issue(),
            cls.post_maintenance_misalignment(),
            cls.low_load_inefficiency(),
        ]
    
    @classmethod
    def get_scenario_by_type(
        cls, 
        failure_type: FailureType,
        duration_days: Optional[int] = None
    ) -> Optional[FailureScenario]:
        """
        Get a specific scenario by its failure type.
        
        Args:
            failure_type: The type of failure to get
            duration_days: Optional custom duration
            
        Returns:
            FailureScenario or None if type not found
        """
        scenario_map = {
            FailureType.HEALTHY: cls.healthy_operation,
            FailureType.TUBE_FOULING: cls.tube_fouling,
            FailureType.BEARING_WEAR: cls.bearing_wear,
            FailureType.REFRIGERANT_LEAK: cls.refrigerant_leak,
            FailureType.ELECTRICAL_ISSUE: cls.electrical_issue,
            FailureType.POST_MAINTENANCE_MISALIGNMENT: cls.post_maintenance_misalignment,
            FailureType.LOW_LOAD_INEFFICIENCY: cls.low_load_inefficiency,
        }
        
        factory = scenario_map.get(failure_type)
        if factory is None:
            return None
        
        if duration_days is not None:
            return factory(duration_days=duration_days)
        return factory()
    
    @classmethod
    def get_scenario_names(cls) -> List[str]:
        """Return list of all scenario names."""
        return [s.name for s in cls.get_all_scenarios()]
