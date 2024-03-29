# -*- coding: utf-8 -*-
"""
Vitaly Lerner, 2019
Simulation of a single neuron expressing ChR2
to a pattern of light activations
Geometry: the slices are coronal, from the right hemisphere
    the coordinates are experiment-oriented

    z: rostral-caudal, z=0 is the top surface of the slice,
        i.e. nose --> 0um ---300um -->  tail
    y: dorsal-ventral, y=0 is the pia, i.e.
        dura --> pia=0um --->900um --> white matter
    x: arbitrary coordinate orthogonal to (y,z) such that approsimately
       x axis is parallel to a local line of pia and wm
       approximately right to left
"""

    
import pandas as pd
from numpy import *
from matplotlib.pyplot import *
import sys,os
if sys.version_info[0]<3:
    PYTHON=2
else:
    PYTHON=3
if os.name=='nt':
    WINDOWS=True
    #print 'WINDOWS!!'
else:
    WINDOWS=False
    
class morphology:
    swc=None
    swc0=None
    branches=None
    segments=None
    meta=None
    
    def segments_geometry(self):
        #combines swc and segments tables
        #to yield the table of the form
        #segment_id,x0,y0,x1,y1,length,dist
        swc=self.swc
        seg=self.segments
        
        swc_iStart=array(seg['start'])
        swc_iEnd=array(seg['end'])
        seg_dist=array(seg['dist'])
        seg_length=array(seg['length'])
        seg_id=array(seg['segment_id'])
        
        swc_pStart=array([ array(swc[swc['id']==ist][['x','y']]) for ist in swc_iStart]).squeeze()
        swc_pEnd=array([ array(swc[swc['id']==ien][['x','y']]) for ien in swc_iEnd]).squeeze()

        geom=pd.DataFrame(data={1:seg_id,           
                                2:swc_pStart[:,0],  3:swc_pStart[:,1],  
                                4:swc_pEnd[:,0],    5:swc_pEnd[:,1],
                                6:seg_length,       7:seg_dist})
                                
        geom.columns=           ['segment_id',
                                 'x0','y0',
                                 'x1','y1',
                                 'length','dist']
        return geom
        
    def soma_geometry(self):

        hbr=array(self.swc[self.swc['id'].isin(list(self.branches[self.branches['parent_branch']==-1]['start']))][['x','y','z']])
         
        CoM=array(mean(matrix(hbr),axis=0))[0]
        R=sqrt(sum((hbr-CoM)**2,axis=1))
        r=0.5*(mean(R)+max(R))
        
        """For debugging purposes
        f=figure()
        #ax=f.add_subplot(111,projection='3d')
        ax = Axes3D(f)
        print r
        phi, theta = np.mgrid[0.0:pi:0.1*pi, 0.0:2.0*pi:0.1*pi]
        x = r*sin(phi)*cos(theta)+CoM[0]
        y = r*sin(phi)*sin(theta)+CoM[1]
        z = r*cos(phi)+CoM[2]
        ax.plot_surface(
        x, y, z,  rstride=1, cstride=1, color='c', alpha=0.4, linewidth=2)

        ax.plot(hbr[:,0],hbr[:,1],hbr[:,2],'x')
        ax.plot([CoM[0]],[CoM[1]],[CoM[2]],'or')
        """
        return CoM,r
        
    def read_swc (self,fSWC):
        #read standard morphology ascii file and
        #return: pandas dataframe of swc
        swc_dt=pd.read_csv(fSWC, skiprows=3,sep='\s',header=None)
        swc_dt.columns=['id','type','x','y','z','r','pid']
        return swc_dt

    def assign(self, fSWC):
        #assign morphology from file
        #store a copy of orginal swc data for reference
        self.swc=self.read_swc(fSWC)
        self.swc0=self.read_swc(fSWC)
        
    def align(self):
        #move the neuron to (0,0)
        #rotate it such that its apical dendrite would reach uniform pia
        #works for pyramidal neurons,
        #won't work for PV
        dt=self.swc
        #extract x,y coordinates of apical dendtite
        xy0=array(dt[:][['x','y']])
        x0=xy0[:,0]
        y0=xy0[:,1]

        xy_apical=array(dt[dt['type']==4][['x','y']])
        xy_soma=array(dt[dt['type']==1][['x','y']])

        #extract x,y coordinates and place soma at (0,0)
        x = xy_apical[:,0]-xy_soma[0,0]
        y = xy_apical[:,1]-xy_soma[0,1]

        #Rough estimation of rotation angle
        p1=polyfit(x,y,1)
        theta=-arctan(p1[0])
        x1=x*cos(theta)-y*sin(theta)
        y1=x*sin(theta)+y*cos(theta)
        if mean(x1)<0:
            x1=-x1
            y1=-y1
            theta+=pi

        #fine estimation of rotation angle
        rng_middle=[i for i,cx in enumerate(x1) if cx>150 and cx<450]
        x2=x1[rng_middle]
        y2=y1[rng_middle]
        p2=polyfit(x2,y2,1)
        theta2=-arctan(p2[0])

        Theta=theta+theta2+pi/2
        x3=x0*cos(Theta)-y0*sin(Theta)
        y3=x0*sin(Theta)+y0*cos(Theta)
        y3-=mean(sorted(y3)[-20:])
        x3-=x3[0]
        self.swc[:]['x']=x3
        self.swc[:]['y']=y3

    def __init__(self,fSWC=None,bAlign=True):
        #Constructor
        if not fSWC==None:
            self.assign(fSWC)
            if bAlign:
                self.align()
            self.branch()
            self.calc_dist()
            self.compartmentalize()

    def translate (self, v):
        #move by a (x,y,z) vector
        self.swc[:]['x']+=v[0]
        self.swc[:]['y']+=v[1]
        self.swc[:]['z']+=v[2]

    def draw(self,params=None):
        #draw using pyplot library

        if params==None:
            Layout='Segments'
            alpha=0.4
        else:
            Layout=params['Layout']
            if 'alpha' in params.keys():
                alpha=params['alpha']
            else:
                alpha=0.4
    
        swc=self.swc

        if Layout=='Points':
            xy0=array(swc[:][['x','y']])
            x0=xy0[:,0]
            y0=xy0[:,1]
            plot(x0,y0,'ok',markersize=.3,alpha=0.2)
            axis('equal')
        elif Layout=='Branches':

            for iBranch in range(len(self.branches)):
                cBr=self.branches.iloc[iBranch,:]
                cBr_ID=array(cBr['branch_id'])

                cBr_SWC=self.branch_swc(cBr_ID)
                cBr_x=array(cBr_SWC['x'])
                cBr_y=array(cBr_SWC['y'])
                cBr_z=array(cBr_SWC['z'])
                cBr_r=array(cBr_SWC['r'])
                plot(cBr_x,cBr_y,'-',markersize=0.05,linewidth=1,alpha=alpha)
        elif Layout=='Soma':
            soma_CoM,soma_r=self.soma_geometry()
            ax=gca()
            ax.add_artist(Circle((soma_CoM[0],soma_CoM[1]),soma_r,alpha=alpha,color=[0.2,0.2,0.2]))
        elif Layout=='Segments':
            seg=self.segments
            for iSeg in range(len(seg)):
                cSeg=seg.iloc[iSeg,:]
                cSeg_start=cSeg['start']
                cSeg_end=cSeg['end']
                cSeg_length=cSeg['length']
                cSeg_dist=cSeg['dist']

                cSeg_start_xy=array(swc[swc['id']==cSeg_start][['x','y']])[0]
                cSeg_start_x=cSeg_start_xy[0]
                cSeg_start_y=cSeg_start_xy[1]

                cSeg_end_xy=array(swc[swc['id']==cSeg_end][['x','y']])[0]
                cSeg_end_x=cSeg_end_xy[0]
                cSeg_end_y=cSeg_end_xy[1]
                cSeg_clr=(200.-cSeg_dist)/200
                if cSeg_clr<0:
                    cSeg_clr=0
                cSeg_clr=cSeg_clr*ones(3)*0.8+0.1
                plot([cSeg_start_x,cSeg_end_x],[cSeg_start_y,cSeg_end_y],color=cSeg_clr,linewidth=cSeg_length/4.)
                #text(cSeg_start_x,cSeg_start_y,'{:.0f}'.format(cSeg_dist),size=8)
                #print cSeg_start_xy,cSeg_end
    def branch_swc(self,branch_id):
        swc=self.swc
        cBr=self.branches[self.branches['branch_id']==int(branch_id)]#.iloc[0,:]
        cBr_Start=int(cBr['start'])
        cBr_End=int(cBr['end'])
        cBr_SWC=swc[ (swc['id']>=cBr_Start) & (swc['id']<=cBr_End)]
        return cBr_SWC

    def euclidian_distance(self,p1,p2):
        return sqrt(sum( (p1-p2)**2))

    def compartmentalize(self):
        swc=self.swc
        br=self.branches
        Seg_cnt=-1
        Seg_DF=[]
        for iBranch in range(len(self.branches)):
            cBr=self.branches.iloc[iBranch,:]
            cBr_ID=array(cBr['branch_id'])
            cBr_SWC=self.branch_swc(cBr_ID)
            cBr_xyzrd=array(cBr_SWC[['x','y','z','r','dist']])
            cBr_x=cBr_xyzrd[:,0]
            cBr_y=cBr_xyzrd[:,1]

            Seg_S=[]#start point
            Seg_E=[]#end point
            Seg_D=[]#Length
            Seg_ID=[]#Segment ID
            Seg_BID=[]#Branch ID
            Seg_RD=[]#distance from root of the chief dendrite

            Seg_start_ind=0
            Seg_cursor=1
            Seg_end_limit=shape(cBr_xyzrd)[0]-1
            Seg_dist=0
            while Seg_cursor<Seg_end_limit:
                while Seg_dist<SEGMENT_LENGTH and Seg_cursor<=Seg_end_limit:
                    p1=cBr_xyzrd[Seg_cursor,:3]
                    p2=cBr_xyzrd[Seg_cursor-1,:3]
                    loc_dist=self.euclidian_distance(p1,p2)
                    Seg_dist+=loc_dist
                    Seg_cursor+=1
                Seg_cnt+=1
                seg_start_ind_global=cBr_SWC.iloc[Seg_start_ind,0]
                seg_end_ind_global=cBr_SWC.iloc[Seg_cursor-1,0]

                seg_dist=mean(cBr_xyzrd[Seg_start_ind:Seg_cursor,4])

                Seg_S.append(seg_start_ind_global)
                Seg_E.append(seg_end_ind_global)
                Seg_D.append(Seg_dist)
                Seg_BID.append(cBr_ID)
                Seg_ID.append(Seg_cnt)
                Seg_RD.append(seg_dist)

                Seg_dist=0
                Seg_start_ind=Seg_cursor
                Seg_cursor+=1
            Seg_DICT={1:Seg_ID,2:Seg_S,3:Seg_E,4:Seg_D,5:Seg_BID,6:Seg_RD}
            Seg_Columns=['segment_id','start','end','length','branch_id','dist']
            Seg=pd.DataFrame(data=Seg_DICT)
            Seg.columns=Seg_Columns
            Seg_DF.append(Seg)
        self.segments=pd.concat(Seg_DF)

    def branch(self):
        #Analyzes swc and finds separate branches
        #finds their start point parent branches
        swc=self.swc
        b0=swc[swc['id']==2]
        B=swc[swc['pid']!=swc['id']-1][1:]
        B=pd.concat([b0,B])
        branch_start=array(B['id'])
        branch_parent_point=array(B['pid'])

        branch_end=branch_start[1:]-1
        branch_end_0=array(swc[-1:]['id'])[0]
        branch_end=hstack([branch_end,[branch_end_0]])

        branch_id=arange(shape(branch_start)[0])

        branch_parent_branch=branch_id*0
        for bID in branch_id:
            bPP=branch_parent_point[bID]
            if bPP==1:
                bBP=-1
            else:
                bBP=[k for k in branch_id if k!=bID and bPP>=branch_start[k] and bPP<branch_end[k] ][0]
            branch_parent_branch[bID]=bBP

        dt={1:branch_id,2:branch_start,3:branch_end,4:branch_parent_point,5:branch_parent_branch}
        structure=pd.DataFrame(data=dt)
        structure.columns=['branch_id','start','end','parent_point','parent_branch']
        self.branches=structure

    def calc_dist(self):
        #calculate distance for each point
        #the distance is calculated from the root of
        #the dendrite
        #add a column to swc to indicate that number

        swc=self.swc
        br=self.branches

        NP=shape(swc)[0]

        dist=pd.DataFrame({'dist':zeros(NP)})

        #swc_ext=pd.concat([swc,dist],axis=1)
        #print swc_ext.head()

        roots=br[br['parent_branch']==-1]

        #initialize queue of branches with roots
        br_pool=array(roots['branch_id'])
        lut=pd.DataFrame(data={'id':[1],'dist':[0]})
        #print lut.head()

        while len(br_pool)>0:
            #dequeue to cBrID
            cBrID=br_pool[0]
            cBr=br[br['branch_id']==cBrID]
            cBr_point_start=int(cBr['start'])
            br_pool=br_pool[1:]
            #print "dequeue\t", cBrID

            cBr_parent_branch=int(cBr['parent_branch'])
            cBr_SWC=self.branch_swc(cBrID)
            if cBr_parent_branch==-1:
                l0=0
            else:
                cBr_parent_point=swc[swc['id']==int(cBr['parent_point'])]
                cBr_parent_point_xyz=array(cBr_parent_point[['x','y','z']])
                cBr_root_point_xyz=array(swc[swc['id']==cBr_point_start][['x','y','z']])
                l00=self.euclidian_distance(cBr_parent_point_xyz,cBr_root_point_xyz)

                cLUT_parent_point=lut[lut['id']==int(cBr['parent_point'])]
                l01=int(cLUT_parent_point['dist'])
                l0=l00+l01

            #find all immideate children in the structure
            #if found, enqueue them
            br_children=array(br[br['parent_branch']==cBrID]['branch_id'])
            if len(br_children)>0:
                br_pool=hstack([br_pool,br_children])

            #calculate each point distance from the root of the branch
            cBr_NP=shape(cBr_SWC)[0]
            cBr_xyz=array(cBr_SWC[['x','y','z']])
            cBr_ds=cumsum( hstack ( [[0],sum((cBr_xyz[1:,:]-cBr_xyz[:-1,:])**2,axis=1)] ))+l0
            cBr_df=pd.DataFrame( data={1:list(cBr_SWC['id']),2:cBr_ds})
            cBr_df.columns=['id','dist']
            lut=pd.concat([lut,cBr_df],ignore_index=True)

        self.swc=pd.merge(swc,lut,how='inner',on='id')

        
    def import_csv(self,base_name):
        if not WINDOWS:
            fSWC_EXT='MORPH/'+base_name+'/swcext.csv'
            fBranches='MORPH/'+base_name+'/branches.csv'
            fSegments='MORPH/'+base_name+'/segments.csv'
        else:
            fSWC_EXT='MORPH//'+base_name+'//swcext.csv'
            fBranches='MORPH//'+base_name+'//branches.csv'
            fSegments='MORPH//'+base_name+'//segments.csv'
        self.swc=pd.read_csv(fSWC_EXT)
        self.branches=pd.read_csv(fBranches)
        self.segments=pd.read_csv(fSegments)
        
    def export_csv(self,base_name):
        fSWC_EXT='MORPH/'+base_name+'/swcext.csv'
        fBranches='MORPH/'+base_name+'/branches.csv'
        fSegments='MORPH/'+base_name+'/segments.csv'
        #fPickle='MORPH/'+base_name+'/morph.pkl'
        
        try:
            shutil.rmtree('MORPH/'+base_name)
        except:
            pass
        try:
            os.rmdir('MORPH/'+base_name)
        except:
            pass
        os.mkdir('MORPH/'+base_name)

        #print '\t', self.meta
        self.branches.to_csv(fBranches,index=False)
        self.swc.to_csv(fSWC_EXT,index=False)
        self.segments.to_csv(fSegments,index=False)
        